"""The LLM in the customer's AI tool (Claude, Copilot, ChatGPT, Gemini) as the world plays it.

It turns a question into a structured query, which it gets wrong now and then, and more often when the question uses
the customer's own word for something and nothing has told it what that word means. Without a pack it reads raw
sheets the way an assistant does: it maps column titles it has seen in many workspaces, guesses the rest, reads a
status picklist it has not seen as best it can, assumes default rules, sometimes counts phase rows as tasks and
archived or non-plan sheets as projects, and miscounts now and then when it aggregates many rows by reading them. A
workspace bigger than its context is cut off.
"""

from __future__ import annotations

import copy
import json

from ..engine import run, tasks
from .sim import CANON, TITLES, VOCABS, World, rng

KNOWN_TITLES = {t.lower() for ts in TITLES["en"].values() for t in ts} | {
    "status",
    "start",
    "ende",
    "fortschritt",
    "statut",
    "début",
    "fin",
    "avancement",
    "responsable",
}
KNOWN_VOCABS = {"ryg", "track", "gar", "de_colours", "ok_watch", "emoji", "fr_colours"}


class Reader:
    def __init__(self, world: World, cfg: dict):
        self.w = world
        self.cfg = cfg

    # ------------------------------------------------------------------------------------------ questions

    def translate(self, q: dict, glossary: dict, salt: str) -> dict:
        r = rng(self.w.seed, "translate", salt, q["id"])
        out = copy.deepcopy(q["query"])
        for term in q["unknown_terms"]:
            miss = r.random() < self.cfg["unknown_term_miss"]  # drawn either way: same luck with or without a glossary
            if miss and term not in glossary:
                if term in ("gate", "checkpoint") and out["entity"] == "milestones":
                    out["entity"] = "tasks"
                if term in ("slipping", "on watch") and out["where"].get("at_risk"):
                    out["where"].pop("at_risk")
                    out["where"]["overdue"] = True
        if r.random() < self.cfg["translate_error"]:
            c = self.w.by_id[q["customer"]]
            projects = [s["name"] for s in c.sheets if c.kinds[s["id"]] == "project"]
            if "project" in out["where"] and len(projects) > 1:
                out["where"]["project"] = projects[(projects.index(out["where"]["project"]) + 1) % len(projects)]
            elif "due_within_days" in out["where"]:
                out["where"]["due_within_days"] = 7
            elif "overdue" in out["where"]:
                out["where"]["overdue"] = False
            else:
                out["where"]["done"] = not out["where"].get("done", False)
        return out

    # ------------------------------------------------------------------------------------------ raw sheets

    def guess_pack(self, cid: str) -> dict:
        """The semantics an assistant reading raw sheets would act on."""
        c = self.w.by_id[cid]
        r = rng(self.w.seed, "guess", cid)
        truth = self.w.truth_pack(cid)
        g = self.cfg
        sheets = {}
        for s in c.sheets:
            kind = c.kinds[s["id"]]
            meta = dict(truth["sheets"][str(s["id"])])
            if kind == "archive":
                obvious = "ARCHIVE" in s["name"].upper()
                meta["kind"] = "archive" if obvious or r.random() > g["includes_archive"] else "project"
            elif kind == "other" and s["name"] == "RAID Log":
                meta["kind"] = "other" if r.random() > g["includes_other"] else "project"
            sheets[str(s["id"])] = meta
        templates = {}
        for sig, t in truth["templates"].items():
            roles = {}
            for role, title in t["roles"].items():
                p = g["known_title"] if title.lower() in KNOWN_TITLES else g["unknown_title"]
                if r.random() < p:
                    roles[role] = title
            vocab = next(k for k, v in VOCABS.items() if set(v) == set(t["status_values"]))
            values = dict(t["status_values"])
            if r.random() > (g["known_vocab"] if vocab in KNOWN_VOCABS else g["unknown_vocab"]):
                order = list(r.permutation(3))
                values = {v: CANON[order[CANON.index(k)]] for v, k in values.items()}
            prog = t["progress"]
            if r.random() > g["progress_scale"]:
                prog = {"fraction": "percent", "percent": "fraction"}.get(prog, prog)
            templates[sig] = dict(t, roles=roles, status_values=values, progress=prog)
        # A raw-sheet reader keeps the RAID log's own columns if it treats it as a plan.
        for s in c.sheets:
            if c.kinds[s["id"]] == "other" and sheets[str(s["id"])]["kind"] == "project":
                cols = {col["type"]: col["title"] for col in s["columns"]}
                sig = f"other-{s['id']}"
                sheets[str(s["id"])]["template"] = sig
                templates[sig] = {
                    "roles": {
                        "task": s["columns"][0]["title"],
                        "owner": cols.get("CONTACT_LIST"),
                        "due": cols.get("DATE"),
                        "status": cols.get("PICKLIST"),
                    },
                    "status_values": {"Open": "at_risk", "Closed": "on_track"},
                    "progress": "fraction",
                    "dates": "iso",
                }
        has_flag = any("milestone" in t["roles"] for t in templates.values())
        rules = {
            "at_risk": {"kind": "status"},
            "fiscal_start_month": 1,
            "done": "progress",
            "milestone": "flag" if has_flag else "zero_duration",
            "summary_rows": "include" if r.random() < g["counts_summary_rows"] else "exclude",
            "project_at_risk_share": 0.01,
        }
        return {"customer": cid, "sheets": sheets, "templates": templates, "rules": rules, "glossary": {}}

    def visible(self, cid: str, pack: dict) -> tuple[dict, int, int]:
        """The sheets that fit in the context, in workspace order: (pack limited to them, tokens, rows read)."""
        c = self.w.by_id[cid]
        g = self.cfg
        budget, used, rows = g["context_tokens"], 0, 0
        p = copy.deepcopy(pack)
        for s in c.sheets:
            meta = p["sheets"][str(s["id"])]
            if meta["kind"] != "project":
                continue
            cost = len(s["rows"]) * len(s["columns"]) * g["tokens_per_cell"] + g["tokens_per_sheet"]
            if used + cost > budget:
                meta["kind"] = "unread"
                continue
            used += cost
            rows += len(s["rows"])
        return p, used, rows

    def read(self, cid: str, pack: dict, query: dict, rows_read: int, salt: str):
        """Answer by reading rows: the engine on what it understood, then a slip that grows with rows aggregated."""
        ws = self.w.workspace(cid)
        rows = tasks(ws, pack)
        ans = run(rows, query, pack["rules"], self.w.today)
        r = rng(self.w.seed, "read", salt, cid, json.dumps(query, sort_keys=True))
        p_slip = 1 - (1 - self.cfg["read_error_per_row"]) ** rows_read
        if r.random() >= p_slip:
            return ans, False
        if isinstance(ans, bool) or ans is None:
            return ans, False
        if isinstance(ans, int):
            return max(0, ans + int(r.choice([-2, -1, 1, 2]))), True
        if isinstance(ans, float):
            return round(ans + float(r.choice([-4.0, -2.5, 2.5, 4.0])), 1), True
        if isinstance(ans, list):
            if ans and r.random() < 0.6:
                return ans[:-1], True
            extra = sorted(
                {x["project"] if query["entity"] == "projects" else x["owner"] or "" for x in rows} - set(ans)
            )
            return sorted(ans + extra[:1]), True
        return ans, False

    # ------------------------------------------------------------------------------------------ status lines

    def draft_slips(self, cid: str, project: str, rows: int, week: int, attempt: int, wcfg: dict) -> bool:
        """Whether an agent drafting one project's weekly status line gets a number or a colour wrong."""
        r = rng(self.w.seed, "draft", cid, project, week, attempt)
        p = 1 - (1 - wcfg["slip"]) * (1 - self.cfg["read_error_per_row"]) ** rows
        return bool(r.random() < p)

    def approver_catches(self, cid: str, project: str, week: int, wcfg: dict) -> bool:
        return bool(rng(self.w.seed, "approve", cid, project, week).random() < wcfg["approver_catch"])
