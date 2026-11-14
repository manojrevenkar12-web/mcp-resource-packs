"""Answers a structured portfolio query over a workspace, using a resource pack for the meaning of every column.

The same engine answers for every design: with the truth pack it produces the labels, with an inferred or reviewed
pack it is what the MCP server's `portfolio_query` tool returns, with the semantics an LLM guessed from raw sheets it
is what that LLM would compute if it read every row without a slip. `server/src/engine.ts` is the TypeScript port;
`tests/test_conformance.py` and `server/test/conformance.test.ts` hold both to the same answers.
"""

from __future__ import annotations

import re
from datetime import date, timedelta

OPS = ("count", "list", "avg_progress", "top_owner")
ENTITIES = ("tasks", "milestones", "projects")
FILTERS = ("project", "owner", "overdue", "at_risk", "done", "due_within_days", "fiscal_quarter")


def parse_date(v, fmt: str) -> date | None:
    if v in (None, ""):
        return None
    if fmt == "dmy_text":
        m = re.fullmatch(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", str(v).strip())
        return date(int(m[3]), int(m[2]), int(m[1])) if m else None
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def parse_progress(v, fmt: str) -> float:
    if v in (None, ""):
        return 0.0
    if fmt == "percent_text":
        m = re.search(r"(\d+(?:[.,]\d+)?)", str(v))
        return float(m[1].replace(",", ".")) / 100 if m else 0.0
    x = float(v)
    return x / 100 if fmt == "percent" else x


def fiscal_quarter(d: date, start_month: int) -> tuple[int, int]:
    shifted = (d.month - start_month) % 12
    year = d.year + (1 if d.month >= start_month and start_month != 1 else 0)
    return year, shifted // 3 + 1


def tasks(workspace: dict, pack: dict) -> list[dict]:
    """Every row of every project sheet, in canonical form, as the pack reads it."""
    rules = pack["rules"]
    out = []
    for s in workspace["sheets"]:
        meta = pack["sheets"].get(str(s["id"]))
        if not meta or meta["kind"] != "project":
            continue
        t = pack["templates"].get(meta["template"])
        if t is None:
            continue
        title = {c["id"]: c["title"] for c in s["columns"]}
        role_of = {v: k for k, v in t["roles"].items()}
        parents = {r["parentId"] for r in s["rows"] if r.get("parentId")}
        for r in s["rows"]:
            if r["id"] in parents and rules.get("summary_rows", "exclude") == "exclude":
                continue
            v = {}
            for cell in r["cells"]:
                role = role_of.get(title.get(cell["columnId"]))
                if role:
                    v[role] = cell["value"]
            start, due = parse_date(v.get("start"), t["dates"]), parse_date(v.get("due"), t["dates"])
            progress = parse_progress(v.get("progress"), t["progress"])
            done = bool(v.get("done")) if rules["done"] == "checkbox" and "done" in t["roles"] else progress >= 0.999
            if rules["milestone"] == "flag" and "milestone" in t["roles"]:
                milestone = bool(v.get("milestone"))
            else:
                milestone = start is not None and start == due
            out.append(
                {
                    "project": s["name"],
                    "name": v.get("task"),
                    "status": t["status_values"].get(v.get("status")),
                    "progress": progress,
                    "start": start,
                    "due": due,
                    "owner": v.get("owner"),
                    "done": done,
                    "milestone": milestone,
                }
            )
    return out


def at_risk(x: dict, rules: dict, today: date) -> bool:
    if x["done"]:
        return False
    if x["status"] in ("at_risk", "off_track"):
        return True
    rule = rules["at_risk"]
    if rule["kind"] == "status_or_due_soon" and x["due"] is not None:
        return 0 <= (x["due"] - today).days <= rule["days"] and x["progress"] < rule["below"]
    return False


def _match(x: dict, where: dict, rules: dict, today: date) -> bool:
    for k, v in where.items():
        if k == "project" and x["project"] != v:
            return False
        if k == "owner" and x["owner"] != v:
            return False
        if k == "done" and x["done"] != v:
            return False
        if k == "overdue" and (not x["done"] and x["due"] is not None and x["due"] < today) != v:
            return False
        if k == "at_risk" and at_risk(x, rules, today) != v:
            return False
        if k == "due_within_days" and not (x["due"] is not None and today <= x["due"] <= today + timedelta(days=v)):
            return False
        if k == "fiscal_quarter":
            fq = fiscal_quarter(today, rules["fiscal_start_month"])
            if x["due"] is None or fiscal_quarter(x["due"], rules["fiscal_start_month"]) != fq:
                return False
    return True


def run(rows: list[dict], query: dict, rules: dict, today: date):
    """Answer one query over canonical rows. Answers are plain JSON values so they compare and serialise."""
    op, entity, where = query["op"], query["entity"], query.get("where", {})
    if entity == "projects":
        # A project is at risk when the share of its open tasks at risk reaches the customer's threshold.
        rest = {k: v for k, v in where.items() if k != "at_risk"}
        by: dict[str, list[dict]] = {}
        for x in rows:
            if _match(x, rest, rules, today):
                by.setdefault(x["project"], []).append(x)
        hit = []
        for name, xs in by.items():
            if "at_risk" in where:
                open_ = [x for x in xs if not x["done"]]
                share = sum(at_risk(x, rules, today) for x in open_) / len(open_) if open_ else 0.0
                if (share >= rules.get("project_at_risk_share", 0.2)) != where["at_risk"]:
                    continue
            hit.append(name)
        hit.sort()
        return hit if op == "list" else len(hit)
    pool = [x for x in rows if (x["milestone"] if entity == "milestones" else True)]
    sel = [x for x in pool if _match(x, where, rules, today)]
    if op == "count":
        return len(sel)
    if op == "list":
        return sorted(f"{x['project']} / {x['name']}" for x in sel)
    if op == "avg_progress":
        return round(100 * sum(x["progress"] for x in sel) / len(sel), 1) if sel else None
    if op == "top_owner":
        counts: dict[str, int] = {}
        for x in sel:
            if x["owner"]:
                counts[x["owner"]] = counts.get(x["owner"], 0) + 1
        if not counts:
            return []
        best = max(counts.values())
        return sorted(o for o, n in counts.items() if n == best)
    raise ValueError(f"unknown op {op}")


def answer(workspace: dict, pack: dict, query: dict, today: date):
    return run(tasks(workspace, pack), query, pack["rules"], today)


def same(a, b) -> bool:
    """Two answers agree: exact for counts and lists, within half a point for an average completion."""
    if isinstance(a, float) or isinstance(b, float):
        return a is not None and b is not None and abs(a - b) <= 0.5
    return a == b
