"""Every design on the same customers, questions and luck. Writes reports/<world>.json.

python scripts/evaluate.py             # the dev world
python scripts/evaluate.py --heldout   # the held-out world, once (writes config/heldout.lock)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from resourcepacks import engine, infer, kits, patterns, review  # noqa: E402
from resourcepacks.settings import load  # noqa: E402
from resourcepacks.world.llm import Reader  # noqa: E402
from resourcepacks.world.sim import World  # noqa: E402

DESIGNS = {
    "generic_mcp": "Assistant reads raw sheets",
    "pack_as_context": "Pack as context, assistant reads rows",
    "drafted_pack": "Drafted pack, query tool",
    "reviewed_pack": "Reviewed pack, query tool",
    "kit": "Full kit: reviewed, workshop, query tool",
}
QUERY_DESIGNS = ("drafted_pack", "reviewed_pack", "kit")


def tokens_of(obj) -> int:
    return len(json.dumps(obj, ensure_ascii=False)) // 4


def served(pack: dict) -> dict:
    return {k: v for k, v in pack.items() if k != "items"}


ROLE_WORDS = {
    "task": "task name",
    "status": "traffic-light status",
    "progress": "completion",
    "start": "start date",
    "due": "due date",
    "owner": "assignee",
    "done": "signed-off box",
    "milestone": "milestone box",
}


def translations(pack: dict, ws: dict) -> list[dict]:
    """What the signed-off pack says this customer's sheets mean, for the console: one line per decision."""
    names = {str(s["id"]): s["name"] for s in ws["sheets"]}
    out = []
    for it in pack["items"]:
        k, v = it["kind"], it["value"]
        if k == "role" and v not in ("task",):
            out.append({"seen": it["key"], "means": ROLE_WORDS.get(v, v), "source": it["source"], "kind": "column"})
        elif k == "status_value":
            out.append({"seen": it["key"], "means": str(v).replace("_", " "), "source": it["source"], "kind": "value"})
        elif k == "sheet_kind" and v != "project":
            out.append(
                {
                    "seen": names.get(it["key"], it["key"]),
                    "means": "archive, left out" if v == "archive" else "not a plan, left out",
                    "source": it["source"],
                    "kind": "sheet",
                }
            )
    r = pack["rules"]
    if r["at_risk"]["kind"] != "status":
        out.append(
            {
                "seen": "at risk",
                "means": f"status, or due in {r['at_risk']['days']} days and under {r['at_risk']['below']:.0%} done",
                "source": "workshop",
                "kind": "rule",
            }
        )
    if r["fiscal_start_month"] != 1:
        month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][
            r["fiscal_start_month"] - 1
        ]
        out.append(
            {
                "seen": "this quarter",
                "means": f"fiscal quarter, year from {month}",
                "source": "workshop",
                "kind": "rule",
            }
        )
    if r["done"] == "checkbox":
        out.append({"seen": "done", "means": "box ticked, not 100%", "source": "workshop", "kind": "rule"})
    for term, std in sorted(pack["glossary"].items()):
        out.append({"seen": f'"{term}"', "means": std.replace("_", " "), "source": "workshop", "kind": "word"})
    seen, uniq = set(), []
    for x in sorted(out, key=lambda x: ({"admin": 0, "workshop": 1}.get(x["source"], 2), x["kind"], x["seen"])):
        if (x["seen"], x["means"]) not in seen:
            seen.add((x["seen"], x["means"]))
            uniq.append(x)
    return uniq[:16]


def evaluate(world_name: str) -> dict:
    wc, cfg = load(world_name), load("packs")
    world = World(wc)
    llm = Reader(world, wc["llm"])
    g, prices, eff = wc["llm"], cfg["prices"], cfg["effort"]
    today = world.today
    per = {d: defaultdict(list) for d in DESIGNS}
    causes = {d: Counter() for d in DESIGNS}
    customers, kits_out, pattern_rows, findings = [], {}, [], defaultdict(set)
    totals = Counter()
    for c in world.customers:
        ws = world.workspace(c.id)
        truth = world.truth_pack(c.id)
        qs = world.questions(c.id)
        drafted = infer.draft(ws, cfg, today)
        reviewed, asked = review.apply_admin(
            drafted, cfg["review_threshold"], lambda it, cid=c.id: world.admin_answer(cid, it)
        )
        full = review.apply_workshop(reviewed, world.workshop(c.id))
        guess = llm.guess_pack(c.id)
        for it in review.queue(drafted, cfg["review_threshold"]):
            findings[(it["kind"], str(it["key"]).lower(), str(world.admin_answer(c.id, it)))].add(c.id)
        packs = {
            "generic_mcp": guess,
            "pack_as_context": full,
            "drafted_pack": drafted,
            "reviewed_pack": reviewed,
            "kit": full,
        }
        rows_of = {s["name"]: len(s["rows"]) for s in ws["sheets"]}
        n_rows = sum(len(s["rows"]) for s in ws["sheets"])
        totals["sheets"] += len(ws["sheets"])
        totals["rows"] += n_rows
        totals["questions"] += len(qs)
        totals["review_items"] += asked
        minutes = {
            "generic_mcp": 0,
            "pack_as_context": asked * eff["review_item"] + eff["workshop"],
            "drafted_pack": 0,
            "reviewed_pack": asked * eff["review_item"],
            "kit": asked * eff["review_item"] + eff["workshop"] + eff["kit_handover"],
        }
        crow = {
            "id": c.id,
            "name": c.name,
            "industry": c.industry,
            "lang": c.lang,
            "regulated": c.regulated,
            "sheets": len(ws["sheets"]),
            "rows": n_rows,
            "templates": len(c.templates),
            "review_items": asked,
            "designs": {},
        }
        detail_kit = []
        for d, pack in packs.items():
            glossary = pack.get("glossary", {})
            reads = d in ("generic_mcp", "pack_as_context")
            if reads:
                vis, ctx_tokens, rows_seen = llm.visible(c.id, pack)
            right = 0
            tok_in = 0
            for q in qs:
                truth_ans = engine.answer(ws, truth, q["query"], today)
                tq = llm.translate(q, glossary, "q")
                if reads:
                    proj = tq["where"].get("project")
                    rows_read = rows_of.get(proj, 0) if proj else rows_seen
                    ans, slipped = llm.read(c.id, vis, tq, rows_read, d)
                    t_in = ctx_tokens + (tokens_of(served(pack)) if d == "pack_as_context" else 0) + 60
                else:
                    ans, slipped = engine.answer(ws, pack, tq, today), False
                    t_in = tokens_of(served(pack)) + 120 + tokens_of(ans)
                ok = engine.same(ans, truth_ans)
                right += ok
                tok_in += t_in
                if d == "kit":
                    detail_kit.append((q, ok))
                if not ok:
                    if tq != q["query"] and not engine.same(engine.answer(ws, truth, tq, today), truth_ans):
                        cause = (
                            "question misread"
                            if not q["unknown_terms"] or set(q["unknown_terms"]) <= set(glossary)
                            else "customer's own word"
                        )
                    elif slipped:
                        cause = "row miscounted while reading"
                    elif reads and not engine.same(
                        engine.answer(ws, vis, q["query"], today), engine.answer(ws, pack, q["query"], today)
                    ):
                        cause = "workspace cut off by the context"
                    else:
                        cause = "wrong semantics"
                    causes[d][cause] += 1
            n = len(qs)
            lower = kits.wilson_lower(right, n, cfg["acceptance"]["z"])
            cost = (
                tok_in * prices["llm_in_per_mtok_eur"] / 1e6
                + n * g["out_tokens"] * prices["llm_out_per_mtok_eur"] / 1e6
            )
            per[d]["right"].append(right)
            per[d]["n"].append(n)
            per[d]["tokens"].append(tok_in)
            per[d]["cost"].append(cost)
            per[d]["minutes"].append(minutes[d])
            per[d]["accepted"].append(lower >= cfg["acceptance"]["target"])
            per[d]["latency"].append(g["latency_base_s"] + tok_in / n / g["prefill_tokens_per_s"])
            crow["designs"][d] = {
                "right": right,
                "questions": n,
                "lower": round(lower, 4),
                "accepted": lower >= cfg["acceptance"]["target"],
                "tokens_per_question": round(tok_in / n),
            }
        # ------------------------------------------------------------------ the weekly status lines
        wcfg, pcfg = wc["writes"], cfg["patterns"]
        projects = [
            (s["name"], len(s["rows"])) for s in ws["sheets"] if truth["sheets"][str(s["id"])]["kind"] == "project"
        ]

        def line(pack, name, ws=ws):
            return tuple(
                engine.answer(ws, pack, {"op": "count", "entity": "tasks", "where": w}, today)
                for w in (
                    {"project": name, "done": False},
                    {"project": name, "overdue": True},
                    {"project": name, "at_risk": True},
                )
            )

        good = {name: line(full, name) == line(truth, name) for name, _ in projects}

        def slips(name, rows, wk, attempt, cid=c.id, wcfg=wcfg):
            return llm.draft_slips(cid, name, rows, wk, attempt, wcfg)

        def catches(name, wk, cid=c.id, wcfg=wcfg):
            return llm.approver_catches(cid, name, wk, wcfg)

        pilot = {
            p: patterns.simulate(p, projects, range(0, pcfg["pilot_weeks"]), slips, catches, pcfg, good.get)
            for p in pcfg["order"]
        }
        ws_answers = world.workshop(c.id)
        chosen, why = patterns.choose(ws_answers["regulated"], ws_answers["tolerance"], pilot)
        live = {
            p: patterns.simulate(
                p, projects, range(pcfg["pilot_weeks"], wcfg["weeks"]), slips, catches, pcfg, good.get
            ).as_dict()
            for p in pcfg["order"]
        }
        pattern_rows.append(
            {
                "customer": c.id,
                "regulated": ws_answers["regulated"],
                "tolerance": ws_answers["tolerance"],
                "projects": len(projects),
                "chosen": chosen,
                "why": why,
                "outcomes": live,
            }
        )
        crow["pattern"] = chosen
        # ------------------------------------------------------------------ the kit, and whether it is done
        kres = crow["designs"]["kit"]
        result = {"right": kres["right"], "questions": kres["questions"], "lower": kres["lower"], "detail": detail_kit}
        meta = {"name": c.name, "sheet_names": {str(s["id"]): s for s in ws["sheets"]}}
        files = kits.build(meta, full, drafted, result, {"chosen": chosen, "why": why}, cfg)
        problems = kits.lint(files, full, result, cfg)
        draft_result = dict(result, lower=crow["designs"]["drafted_pack"]["lower"])
        draft_problems = kits.lint(
            kits.build(meta, drafted, drafted, draft_result, {"chosen": chosen, "why": why}, cfg),
            drafted,
            draft_result,
            cfg,
        )
        kits_out[c.id] = {
            "ready": not problems,
            "problems": problems,
            "draft_problems": len(draft_problems),
            "runbook_steps": files["RUNBOOK.md"].count("## Step"),
            "questions_for_admin": asked,
        }
        crow["kit_ready"] = not problems
        # Agents write only for customers whose kit is done: the checker is only as right as the pack it checks with
        # (held-out finding, docs/heldout.md).
        pattern_rows[-1]["switched_on"] = not problems
        crow["translations"] = translations(full, ws)
        customers.append(crow)

    designs = {}
    for d in DESIGNS:
        p = per[d]
        n = sum(p["n"])
        designs[d] = {
            "right": sum(p["right"]),
            "questions": n,
            "accuracy": round(sum(p["right"]) / n, 4),
            "customers_accepted": sum(p["accepted"]),
            "customers": len(p["accepted"]),
            "tokens_per_question": round(sum(p["tokens"]) / n),
            "cost_per_1000_questions_eur": round(1000 * sum(p["cost"]) / n, 2),
            "latency_s": round(sum(p["latency"]) / len(p["latency"]), 2),
            "consultant_hours_per_customer": round(sum(p["minutes"]) / 60 / len(p["minutes"]), 2),
            "wrong_by_cause": dict(causes[d].most_common()),
        }
    pat = {p: Counter() for p in cfg["patterns"]["order"] + ["chosen"]}
    for row in pattern_rows:
        chosen_rows = [("chosen", row["outcomes"][row["chosen"]])] if row["switched_on"] else []
        pat["chosen"]["held_back"] += int(not row["switched_on"])
        for p, o in list(row["outcomes"].items()) + chosen_rows:
            for k in ("lines", "wrong", "llm_calls", "person_minutes"):
                pat[p][k] += o[k]
        pat["chosen"]["over_tolerance"] += int(
            row["switched_on"]
            and row["outcomes"][row["chosen"]]["wrong_rate"] > row["tolerance"]
            and not row["regulated"]
        )
    proposals = [
        {"kind": k, "key": key, "answer": ans, "customers": sorted(cs)}
        for (k, key, ans), cs in sorted(findings.items(), key=lambda kv: (-len(kv[1]), kv[0]))
        if len(cs) >= 2
    ]
    rule_defaults = load("packs")["defaults"]
    non_default = Counter()
    for c in world.customers:
        r = c.rules
        non_default["at_risk"] += r["at_risk"]["kind"] != "status"
        non_default["fiscal_start_month"] += r["fiscal_start_month"] != 1
        non_default["project_at_risk_share"] += r["project_at_risk_share"] != rule_defaults["project_at_risk_share"]
        non_default["glossary"] += bool(c.glossary)
    return {
        "world": wc["name"],
        "volume": {
            "customers": len(world.customers),
            "sheets": totals["sheets"],
            "rows": totals["rows"],
            "questions": totals["questions"],
            "languages": sorted({c.lang for c in world.customers}),
            "regulated": sum(c.regulated for c in world.customers),
            "with_legacy_template": sum(len(c.templates) > 1 for c in world.customers),
            "review_items": totals["review_items"],
        },
        "designs": designs,
        "customers": customers,
        "patterns": {"per_customer": pattern_rows, "totals": {k: dict(v) for k, v in pat.items()}},
        "kits": {"ready": sum(k["ready"] for k in kits_out.values()), "total": len(kits_out), "per_customer": kits_out},
        "findings": {
            "proposals": proposals[:12],
            "rules_not_default": dict(non_default),
            "customers": len(world.customers),
        },
        "target": cfg["acceptance"]["target"],
    }


def code_hash() -> str:
    h = hashlib.sha256()
    for p in sorted((ROOT / "src").rglob("*.py")) + sorted((ROOT / "config").glob("packs.toml")):
        h.update(p.read_bytes())
    return h.hexdigest()[:16]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--heldout", action="store_true")
    a = ap.parse_args()
    name = "heldout" if a.heldout else "world"
    lock = ROOT / "config" / "heldout.lock"
    if a.heldout and lock.exists():
        sys.exit(f"The held-out world was already run ({lock.read_text().strip()}). Measure changes on the dev world.")
    r = evaluate(name)
    out = ROOT / "reports" / ("heldout.json" if a.heldout else "dev.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(r, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    if a.heldout:
        rev = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT
        ).stdout.strip()
        lock.write_text(f"commit {rev or 'uncommitted'} code {code_hash()}\n")
    for d, v in r["designs"].items():
        print(
            f"{d:16} {v['accuracy']:.3f} right  {v['customers_accepted']:2}/{v['customers']} accepted  "
            f"{v['tokens_per_question']:7} tok/q  €{v['cost_per_1000_questions_eur']:7.2f}/1000q  {v['consultant_hours_per_customer']:.2f} h  {v['wrong_by_cause']}"
        )
    print("kits ready", r["kits"]["ready"], "/", r["kits"]["total"])
    for p, v in r["patterns"]["totals"].items():
        print(p, v)


if __name__ == "__main__":
    main()
