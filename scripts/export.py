"""Writes what the server, its tests and a reader of the repo need from the dev world:

- data/example/workspace.json and pack.json: one customer's workspace snapshot and its signed-off pack, for the demo
  server (`npm start` with PACK and SNAPSHOT);
- server/test/fixtures/conformance.json: that workspace, the pack under several rule variants, and queries with the
  Python engine's answers, which the TypeScript engine must reproduce;
- kits/<customer>/: the example Deployment Kit for that customer.
"""

from __future__ import annotations

import copy
import itertools
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from resourcepacks import engine, infer, kits, patterns, review  # noqa: E402
from resourcepacks.settings import load  # noqa: E402
from resourcepacks.world.llm import Reader  # noqa: E402
from resourcepacks.world.sim import World  # noqa: E402

EXAMPLE = "C08"  # a German customer with questions for its admin
PHASES = "C06"  # a small customer whose tasks hang under phase rows


def dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def main() -> None:
    wc, cfg = load("world"), load("packs")
    world = World(wc)
    llm = Reader(world, wc["llm"])
    c = world.by_id[EXAMPLE]
    ws = world.workspace(EXAMPLE)
    drafted = infer.draft(ws, cfg, world.today)
    reviewed, _ = review.apply_admin(drafted, cfg["review_threshold"], lambda it: world.admin_answer(EXAMPLE, it))
    full = review.apply_workshop(reviewed, world.workshop(EXAMPLE))
    served = {k: v for k, v in full.items() if k != "items"}
    dump(ROOT / "data" / "example" / "workspace.json", ws)
    dump(ROOT / "data" / "example" / "pack.json", served)

    # conformance: a workspace with phase rows under rule variants that exercise every branch of the engine
    workspaces, variants, cases = {}, {}, []
    for cid in (PHASES,):
        cws = world.workspace(cid)
        workspaces[cid] = cws
        d = infer.draft(cws, cfg, world.today)
        rv, _ = review.apply_admin(d, cfg["review_threshold"], lambda it, cid=cid: world.admin_answer(cid, it))
        signed = {k: v for k, v in review.apply_workshop(rv, world.workshop(cid)).items() if k != "items"}
        variants[f"{cid}:signed_off"] = signed
        for name, change in {
            "due_soon_rule": {"at_risk": {"kind": "status_or_due_soon", "days": 14, "below": 0.9}},
            "status_rule": {"at_risk": {"kind": "status"}},
            "fiscal_march": {"fiscal_start_month": 3},
            "fiscal_february": {"fiscal_start_month": 2},
            "done_by_progress": {"done": "progress"},
            "milestone_by_duration": {"milestone": "zero_duration"},
            "phase_rows_counted": {"summary_rows": "include"},
        }.items():
            v = copy.deepcopy(signed)
            v["rules"].update(change)
            if v["rules"] != signed["rules"]:
                variants[f"{cid}:{name}"] = v
        projects = sorted({s["name"] for s in cws["sheets"] if signed["sheets"][str(s["id"])]["kind"] == "project"})
        owners = sorted(world.by_id[cid].owners)
        queries = [q["query"] for q in world.questions(cid)]
        for op, ent in itertools.product(("count", "list"), ("tasks", "milestones", "projects")):
            for where in (
                {},
                {"overdue": True},
                {"at_risk": True},
                {"done": False, "due_within_days": 30},
                {"fiscal_quarter": "current"},
            ):
                queries.append({"op": op, "entity": ent, "where": where})
        for p in projects[:4]:
            queries.append({"op": "avg_progress", "entity": "tasks", "where": {"project": p}})
            queries.append({"op": "top_owner", "entity": "tasks", "where": {"project": p, "done": False}})
        for o in owners[:3]:
            queries.append({"op": "count", "entity": "tasks", "where": {"owner": o, "done": False}})
        for name, pack in variants.items():
            if name.startswith(cid + ":"):
                for q in queries:
                    cases.append({"variant": name, "query": q, "answer": engine.answer(cws, pack, q, world.today)})
    dump(
        ROOT / "server" / "test" / "fixtures" / "conformance.json",
        {"today": world.today.isoformat(), "workspaces": workspaces, "packs": variants, "cases": cases},
    )

    # the example kit
    qs = world.questions(EXAMPLE)
    detail = []
    for q in qs:
        tq = llm.translate(q, full["glossary"], "q")
        detail.append(
            (
                q,
                engine.same(
                    engine.answer(ws, full, tq, world.today),
                    engine.answer(ws, world.truth_pack(EXAMPLE), q["query"], world.today),
                ),
            )
        )
    right = sum(ok for _, ok in detail)
    result = {
        "right": right,
        "questions": len(qs),
        "lower": kits.wilson_lower(right, len(qs), cfg["acceptance"]["z"]),
        "detail": detail,
    }
    wcfg, pcfg = wc["writes"], cfg["patterns"]
    projs = [(s["name"], len(s["rows"])) for s in ws["sheets"] if served["sheets"][str(s["id"])]["kind"] == "project"]
    pilot = {
        p: patterns.simulate(
            p,
            projs,
            range(pcfg["pilot_weeks"]),
            lambda n, r, wk, a: llm.draft_slips(EXAMPLE, n, r, wk, a, wcfg),
            lambda n, wk: llm.approver_catches(EXAMPLE, n, wk, wcfg),
            pcfg,
            lambda n: True,
        )
        for p in pcfg["order"]
    }
    w = world.workshop(EXAMPLE)
    chosen, why = patterns.choose(w["regulated"], w["tolerance"], pilot)
    meta = {"name": c.name, "sheet_names": {str(s["id"]): s for s in ws["sheets"]}}
    files = kits.build(meta, full, drafted, result, {"chosen": chosen, "why": why}, cfg)
    out = ROOT / "kits" / EXAMPLE
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for name, text in files.items():
        (out / name).write_text(text)


if __name__ == "__main__":
    main()
