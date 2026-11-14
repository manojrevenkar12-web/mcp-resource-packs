"""Customers, their Smartsheet workspaces, and the truth about every one.

Each customer has its own way of running projects in Smartsheet: what the status column is called and what its
values mean, whether progress is 0.45 or 45, whether tasks hang under phase rows, how finished projects are archived,
which sheets in the workspace are not project plans at all, and rules nobody wrote into a sheet (what "at risk" means
here, when the fiscal year starts, whether "done" is a tick box or 100%). Many have an older template on older
projects.

The world renders each workspace in the shape the Smartsheet API returns (sheets, columns with types, rows with
parent ids and cells keyed by column id), and it plays the people a consultant talks to: the customer's admin who
answers review questions, and the workshop where the rules come out. It also holds the truth pack: the semantics a
perfect consultant would write down. Only scripts/evaluate.py, scripts/export.py and the tests import this module.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date, timedelta

import numpy as np

ROLES = ("task", "status", "progress", "start", "due", "owner", "done", "milestone")
CANON = ("on_track", "at_risk", "off_track")


def rng(*keys) -> np.random.Generator:
    h = hashlib.blake2b("/".join(map(str, keys)).encode(), digest_size=8).digest()
    return np.random.default_rng(int.from_bytes(h, "little"))


def pick(r, xs):
    return xs[int(r.integers(len(xs)))]


# ---------------------------------------------------------------------------------------------- conventions in use

TITLES = {
    "en": {
        "task": ["Task Name", "Task", "Activity", "Deliverable", "Work Item"],
        "status": ["Status", "RAG", "Health", "Project Health", "Traffic Light"],
        "progress": ["% Complete", "Progress", "Percent Complete", "Completion"],
        "start": ["Start", "Start Date", "Begin"],
        "due": ["End Date", "Finish", "Due Date", "Target Date", "Due"],
        "owner": ["Assigned To", "Owner", "Responsible", "Lead"],
        "done": ["Done", "Complete?", "Closed"],
        "milestone": ["Milestone", "Key Date", "Gate"],
    },
    "de": {
        "task": ["Aufgabe", "Vorgang", "Arbeitspaket"],
        "status": ["Status", "Ampel", "Zustand"],
        "progress": ["% Fertig", "Fortschritt", "Erledigt %"],
        "start": ["Start", "Beginn", "Startdatum"],
        "due": ["Ende", "Fällig", "Enddatum", "Termin"],
        "owner": ["Zuständig", "Verantwortlich", "Bearbeiter"],
        "done": ["Erledigt", "Abgeschlossen"],
        "milestone": ["Meilenstein", "Gate"],
    },
    "fr": {
        "task": ["Tâche", "Activité", "Livrable"],
        "status": ["Statut", "Météo", "Santé"],
        "progress": ["% Achevé", "Avancement"],
        "start": ["Début", "Date de début"],
        "due": ["Fin", "Échéance"],
        "owner": ["Responsable", "Assigné à"],
        "done": ["Terminé", "Clôturé"],
        "milestone": ["Jalon"],
    },
}

VOCABS = {
    "ryg": ("Green", "Yellow", "Red"),
    "track": ("On Track", "At Risk", "Off Track"),
    "gar": ("G", "A", "R"),
    "de_colours": ("Grün", "Gelb", "Rot"),
    "ok_watch": ("OK", "Watch", "Critical"),
    "custom_plan": ("On Plan", "Slipping", "Blocked"),
    # held-out only
    "emoji": ("🟢", "🟡", "🔴"),
    "fr_colours": ("Vert", "Orange", "Rouge"),
    "healthy": ("Healthy", "Concern", "Escalated"),
}

NOISE = ["Comments", "Predecessors", "Duration", "Budget", "Notes", "Attachments"]

OTHER_SHEETS = {
    "RAID Log": [
        ("Item", "TEXT_NUMBER"),
        ("Type", "PICKLIST"),
        ("Owner", "CONTACT_LIST"),
        ("Status", "PICKLIST"),
        ("Raised", "DATE"),
    ],
    "Project Intake": [
        ("Request", "TEXT_NUMBER"),
        ("Requester", "CONTACT_LIST"),
        ("Submitted", "DATE"),
        ("Priority", "PICKLIST"),
        ("Status", "PICKLIST"),
    ],
    "Resource Plan": [
        ("Name", "TEXT_NUMBER"),
        ("Role", "TEXT_NUMBER"),
        ("Capacity %", "TEXT_NUMBER"),
        ("Allocation", "TEXT_NUMBER"),
    ],
}

INDUSTRIES = [
    ("pharma", True),
    ("public sector", True),
    ("bank", True),
    ("construction", False),
    ("agency", False),
    ("software", False),
    ("manufacturing", False),
    ("retail", False),
    ("energy", False),
    ("logistics", False),
]
NAMES = [
    "Northwind",
    "Contoso",
    "Fabrikam",
    "Tailspin",
    "Adatum",
    "Litware",
    "Proseware",
    "Wingtip",
    "Lucerne",
    "Margie",
    "Alpine",
    "Coho",
    "Fourth",
    "Wide World",
    "Trey",
    "Humongous",
    "Blue Yonder",
    "Datum",
]
FIRST = [
    "Anna",
    "Ben",
    "Clara",
    "David",
    "Elif",
    "Felix",
    "Greta",
    "Hassan",
    "Ines",
    "Jonas",
    "Katja",
    "Luca",
    "Mira",
    "Noah",
    "Olga",
    "Paul",
    "Rosa",
    "Sven",
    "Tara",
    "Umut",
    "Vera",
    "Yusuf",
]
LAST = [
    "Schmidt",
    "Weber",
    "Novak",
    "Rossi",
    "Kaya",
    "Meyer",
    "Fischer",
    "Dubois",
    "Jansen",
    "Wagner",
    "Becker",
    "Hoffmann",
    "Petrov",
    "Silva",
    "Kraus",
    "Lang",
]
WORDS_A = [
    "Plant",
    "ERP",
    "Website",
    "Warehouse",
    "Clinic",
    "Branch",
    "Data",
    "Line",
    "Store",
    "Fleet",
    "Portal",
    "Network",
    "Lab",
    "Site",
    "Office",
    "Billing",
    "CRM",
    "Payroll",
]
WORDS_B = [
    "Upgrade",
    "Rollout",
    "Relaunch",
    "Migration",
    "Setup",
    "Expansion",
    "Refit",
    "Consolidation",
    "Launch",
    "Audit",
    "Integration",
    "Renewal",
    "Cutover",
    "Pilot",
]
TERMS = {
    "project": ["project", "workstream", "initiative"],
    "milestone": ["milestone", "gate", "key date", "checkpoint"],
    "at_risk": ["at risk", "amber", "slipping", "on watch"],
}
UNKNOWN_TERMS = {"gate", "checkpoint", "slipping", "on watch"}


# ---------------------------------------------------------------------------------------------- the customer


@dataclass
class Template:
    sig: str
    titles: dict[str, str]
    vocab: str
    progress: str
    dates: str
    has_done: bool
    has_milestone: bool
    noise: list[str]


@dataclass
class Customer:
    id: str
    name: str
    industry: str
    regulated: bool
    lang: str
    templates: list[Template]
    hierarchy: bool
    archive_style: str
    rules: dict
    glossary: dict[str, str]  # customer term -> standard term
    terms: dict[str, str]  # standard term -> the word this customer uses
    owners: list[str]
    tolerance: float  # wrong status lines a customer accepts in its weekly roll-up
    sheets: list[dict] = field(default_factory=list)
    kinds: dict[int, str] = field(default_factory=dict)
    sheet_template: dict[int, str] = field(default_factory=dict)


class World:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.seed = cfg["seed"]
        self.today = date.fromisoformat(cfg["today"])
        self.customers = [self._customer(i) for i in range(cfg["customers"])]
        self.by_id = {c.id: c for c in self.customers}
        for c in self.customers:
            self._workspace(c)

    # ------------------------------------------------------------------------------------------ customers

    def _template(self, r, lang: str, sig: str, avoid: Template | None = None) -> Template:
        cfg = self.cfg
        while True:
            titles = {role: pick(r, TITLES[lang][role]) for role in ROLES}
            if len(set(titles.values())) == len(titles):
                break
        vocab = pick(r, cfg["status_vocabs"])
        if lang == "de" and r.random() < 0.5 and "de_colours" in cfg["status_vocabs"]:
            vocab = "de_colours"
        if lang == "fr" and "fr_colours" in cfg["status_vocabs"] and r.random() < 0.5:
            vocab = "fr_colours"
        t = Template(
            sig=sig,
            titles=titles,
            vocab=vocab,
            progress=pick(r, cfg["progress_formats"]),
            dates=pick(r, cfg["date_formats"]) if avoid is not None else "iso",
            has_done=bool(r.random() < 0.45),
            has_milestone=bool(r.random() < 0.55),
            noise=[n for n in NOISE if r.random() < 0.4],
        )
        if avoid is not None and t.titles == avoid.titles:
            t.titles = dict(
                t.titles, status=pick(r, [x for x in TITLES[lang]["status"] if x != avoid.titles["status"]])
            )
        return t

    def _customer(self, i: int) -> Customer:
        cfg = self.cfg
        r = rng(self.seed, "customer", i)
        industry, regulated = pick(r, INDUSTRIES)
        regulated = regulated if r.random() < cfg["regulated_share"] * 2.2 else False
        lang = pick(r, cfg["languages"])
        main = self._template(r, lang, "T1")
        templates = [main]
        if r.random() < cfg["legacy_share"]:
            templates.append(self._template(r, lang, "T0", avoid=main))
        done_rule = "checkbox" if main.has_done and r.random() < 0.7 else "progress"
        at_risk = (
            {"kind": "status"}
            if r.random() < 0.5
            else {"kind": "status_or_due_soon", "days": int(pick(r, [7, 14])), "below": float(pick(r, [0.8, 0.9]))}
        )
        rules = {
            "at_risk": at_risk,
            "fiscal_start_month": int(pick(r, [1, 1, 2, 4, 7, 10])),
            "done": done_rule,
            "milestone": "flag" if main.has_milestone else "zero_duration",
            "summary_rows": "exclude",
            "project_at_risk_share": float(pick(r, [0.15, 0.25, 0.35])),
        }
        terms = {k: (v[0] if r.random() < 0.4 else pick(r, v[1:])) for k, v in TERMS.items()}
        glossary = {v: k for k, v in terms.items() if v != k.replace("_", " ")}
        owners = []
        while len(owners) < int(r.integers(6, 15)):
            n = f"{pick(r, FIRST)} {pick(r, LAST)}"
            if n not in owners:
                owners.append(n)
        name = f"{NAMES[i % len(NAMES)]} {industry.title()}" if i < len(NAMES) else f"Customer {i}"
        return Customer(
            id=f"C{i + 1:02d}",
            name=name,
            industry=industry,
            regulated=regulated,
            lang=lang,
            templates=templates,
            hierarchy=bool(r.random() < cfg["hierarchy_share"]),
            archive_style=pick(r, cfg["archive_styles"]),
            rules=rules,
            glossary=glossary,
            terms=terms,
            owners=owners,
            tolerance=float(pick(r, [0.0, 0.01, 0.05])),
        )

    # ------------------------------------------------------------------------------------------ workspace

    def _tasks(self, r, c: Customer, t: Template, archived: bool) -> list[dict]:
        """Canonical rows of one project: what is really true about every task."""
        n = int(r.integers(*self.cfg["tasks"]))
        anchor = self.today - timedelta(days=int(r.integers(400, 700) if archived else r.integers(20, 200)))
        rows = []
        phases = int(r.integers(3, 6)) if c.hierarchy else 0
        for k in range(n):
            start = anchor + timedelta(days=int(r.integers(0, 300 if not archived else 200)))
            milestone = bool(r.random() < 0.09)
            if milestone:
                dur = 0
            elif c.rules["milestone"] == "zero_duration":
                dur = int(r.integers(1, 30))
            else:
                dur = int(r.integers(0, 30))
            due = start + timedelta(days=dur)
            if archived or due < self.today - timedelta(days=int(r.integers(0, 40))):
                progress = 1.0 if (archived or r.random() < 0.8) else float(np.round(r.uniform(0.3, 0.95), 2))
            elif start > self.today:
                progress = 0.0
            else:
                progress = float(np.round(r.uniform(0.0, 0.95), 2))
            if milestone:
                progress = 1.0 if due < self.today and r.random() < 0.8 else (0.0 if due >= self.today else progress)
            if c.rules["done"] == "checkbox":
                # people tick the box and forget the %, or type 100% before the work is signed off
                done = progress >= 1.0 or (progress >= 0.7 and r.random() < 0.5)
                if progress >= 1.0 and not archived and r.random() < 0.1:
                    done = False
            else:
                done = progress >= 1.0
            if done:
                status = "on_track"
            else:
                late = due < self.today
                p = [0.35, 0.35, 0.3] if late else [0.72, 0.2, 0.08]
                status = CANON[int(r.choice(3, p=p))]
            rows.append(
                {
                    "name": f"{'Milestone: ' if milestone and r.random() < 0.3 else ''}{pick(r, WORDS_A)} {pick(r, ['design', 'build', 'test', 'sign-off', 'training', 'review', 'handover', 'procurement', 'go-live', 'data load'])} {k + 1}",
                    "start": start,
                    "due": due,
                    "progress": progress,
                    "status": status,
                    "owner": pick(r, c.owners),
                    "done": bool(done),
                    "milestone": milestone,
                    "phase": int(k * phases / n) if phases else None,
                }
            )
        return rows

    def _workspace(self, c: Customer) -> None:
        r = rng(self.seed, "workspace", c.id)
        n_projects = int(r.integers(*self.cfg["projects"]))
        used = set()
        sid = 1000 * int(c.id[1:])
        plans = []
        for k in range(n_projects + int(r.integers(*self.cfg["archive_sheets"]))):
            while True:
                pname = f"{pick(r, WORDS_A)} {pick(r, WORDS_B)}"
                if pname not in used:
                    used.add(pname)
                    break
            archived = k >= n_projects
            t = c.templates[-1] if len(c.templates) > 1 and (archived or r.random() < 0.35) else c.templates[0]
            if archived:
                pname = {
                    "prefix": f"ARCHIVE - {pname}",
                    "suffix_old": f"zz_{pname} (old)",
                    "closed": f"{pname} [closed]",
                    "year": f"{pname} 2024",
                }[c.archive_style]
            plans.append((pname, t, archived))
        for pname, t, archived in plans:
            sid += 1
            rows = self._tasks(rng(self.seed, "tasks", c.id, pname), c, t, archived)
            c.sheets.append(self._render(sid, pname, t, rows, c))
            c.kinds[sid] = "archive" if archived else "project"
            c.sheet_template[sid] = t.sig
        for oname in list(OTHER_SHEETS)[: int(r.integers(1, 4))]:
            sid += 1
            c.sheets.append(self._render_other(sid, oname, c, r))
            c.kinds[sid] = "other"

    def _cell(self, role: str, value, t: Template):
        if value is None:
            return None
        if role in ("start", "due"):
            return value.isoformat() if t.dates == "iso" else value.strftime("%d.%m.%Y")
        if role == "progress":
            if t.progress == "fraction":
                return round(value, 2)
            if t.progress == "percent":
                return round(value * 100)
            return f"{round(value * 100)} %"
        if role == "status":
            return VOCABS[t.vocab][CANON.index(value)]
        if role == "owner":
            return value
        return value

    def _render(self, sid: int, name: str, t: Template, rows: list[dict], c: Customer) -> dict:
        roles = [ro for ro in ROLES if (ro != "done" or t.has_done) and (ro != "milestone" or t.has_milestone)]
        types = {
            "task": "TEXT_NUMBER",
            "status": "PICKLIST",
            "progress": "TEXT_NUMBER",
            "owner": "CONTACT_LIST",
            "done": "CHECKBOX",
            "milestone": "CHECKBOX",
            "start": "DATE" if t.dates == "iso" else "TEXT_NUMBER",
            "due": "DATE" if t.dates == "iso" else "TEXT_NUMBER",
        }
        cols = []
        for ro in roles:
            col = {"id": sid * 100 + len(cols), "title": t.titles[ro], "type": types[ro]}
            if ro == "task":
                col["primary"] = True
            if ro == "status":
                col["options"] = self._option_order(t)
                if t.vocab == "ryg":
                    col["symbol"] = "RYG"
            cols.append(col)
        for nz in t.noise:
            cols.append({"id": sid * 100 + len(cols), "title": nz, "type": "TEXT_NUMBER"})
        cid = {col["title"]: col["id"] for col in cols}
        out_rows = []
        rid = sid * 10000
        phase_ids = {}
        if c.hierarchy:
            for ph in sorted({x["phase"] for x in rows}):
                kids = [x for x in rows if x["phase"] == ph]
                rid += 1
                phase_ids[ph] = rid
                summary = {
                    "task": f"Phase {ph + 1}",
                    "start": min(x["start"] for x in kids),
                    "due": max(x["due"] for x in kids),
                    "progress": round(float(np.mean([x["progress"] for x in kids])), 2),
                    "status": CANON[max(CANON.index(x["status"]) for x in kids)],
                    "owner": None,
                    "done": all(x["done"] for x in kids),
                    "milestone": False,
                }
                out_rows.append({"id": rid, "parentId": None, "cells": self._cells(summary, roles, t, cid)})
        for x in rows:
            rid += 1
            v = dict(x, task=x["name"])
            out_rows.append(
                {"id": rid, "parentId": phase_ids.get(x["phase"]), "cells": self._cells(v, roles, t, cid, x)}
            )
        return {"id": sid, "name": name, "columns": cols, "rows": out_rows}

    def _option_order(self, t: Template) -> list[str]:
        """Admins order picklists as they like: good to bad, bad to good, or alphabetically."""
        opts = list(VOCABS[t.vocab])
        u = rng(self.seed, "options", t.sig, t.vocab, t.titles["status"]).random()
        if u < 0.3:
            return opts[::-1]
        if u < 0.45:
            return sorted(opts)
        return opts

    def _cells(self, v: dict, roles, t: Template, cid: dict, src: dict | None = None) -> list[dict]:
        cells = [{"columnId": cid[t.titles[ro]], "value": self._cell(ro, v.get(ro), t)} for ro in roles]
        for nz in t.noise:
            val = {"Duration": f"{(v['due'] - v['start']).days}d", "Budget": None}.get(nz, "")
            cells.append({"columnId": cid[nz], "value": val})
        return cells

    def _render_other(self, sid: int, name: str, c: Customer, r) -> dict:
        cols = [{"id": sid * 100 + i, "title": t, "type": ty} for i, (t, ty) in enumerate(OTHER_SHEETS[name])]
        cols[0]["primary"] = True
        rows = []
        for k in range(int(r.integers(8, 40))):
            cells = []
            for col in cols:
                ty = col["type"]
                val = {
                    "DATE": (self.today - timedelta(days=int(r.integers(0, 200)))).isoformat(),
                    "CONTACT_LIST": pick(r, c.owners),
                    "PICKLIST": pick(r, ["Open", "Closed", "New", "Approved", "High", "Low"]),
                }.get(ty, f"{name} item {k + 1}" if col.get("primary") else str(int(r.integers(10, 100))))
                cells.append({"columnId": col["id"], "value": val})
            rows.append({"id": sid * 10000 + k + 1, "parentId": None, "cells": cells})
        return {"id": sid, "name": name, "columns": cols, "rows": rows}

    # ------------------------------------------------------------------------------------------ what people say

    def workspace(self, cid: str) -> dict:
        c = self.by_id[cid]
        return {"customer": cid, "name": c.name, "sheets": c.sheets}

    def truth_pack(self, cid: str) -> dict:
        """The semantics a perfect consultant would write down for this customer."""
        c = self.by_id[cid]
        templates = {}
        for t in c.templates:
            roles = {
                ro: t.titles[ro]
                for ro in ROLES
                if (ro != "done" or t.has_done) and (ro != "milestone" or t.has_milestone)
            }
            templates[t.sig] = {
                "roles": roles,
                "status_values": {v: CANON[i] for i, v in enumerate(VOCABS[t.vocab])},
                "progress": t.progress,
                "dates": t.dates,
            }
        return {
            "customer": cid,
            "sheets": {
                str(s["id"]): {"kind": c.kinds[s["id"]], "template": c.sheet_template.get(s["id"])} for s in c.sheets
            },
            "templates": templates,
            "rules": dict(c.rules),
            "glossary": dict(c.glossary),
        }

    def admin_answer(self, cid: str, item: dict):
        """What the customer's Smartsheet admin says when a consultant asks about one review item."""
        p = self.truth_pack(cid)
        kind, key = item["kind"], item["key"]
        if kind == "sheet_kind":
            return p["sheets"][key]["kind"]
        sig = p["sheets"][item["sheet"]]["template"]
        t = p["templates"][sig]
        if kind == "role":
            return next((ro for ro, title in t["roles"].items() if title == key), None)
        if kind == "status_value":
            return t["status_values"].get(key)
        if kind == "progress":
            return t["progress"]
        if kind == "dates":
            return t["dates"]
        raise KeyError(kind)

    def workshop(self, cid: str) -> dict:
        """What comes out of the customer workshop: the rules nobody wrote into a sheet, and their own words."""
        c = self.by_id[cid]
        return {
            "rules": dict(c.rules),
            "glossary": dict(c.glossary),
            "regulated": c.regulated,
            "tolerance": c.tolerance,
        }

    # ------------------------------------------------------------------------------------------ questions

    def questions(self, cid: str) -> list[dict]:
        """What this customer's people ask their AI assistant, with the query that answers each."""
        c = self.by_id[cid]
        r = rng(self.seed, "questions", cid)
        projects = [s["name"] for s in c.sheets if c.kinds[s["id"]] == "project"]
        out = []
        for k in range(self.cfg["questions_per_customer"]):
            words = {
                key: (c.terms[key] if r.random() < self.cfg["glossary_share"] else key.replace("_", " "))
                for key in TERMS
            }
            P, O = pick(r, projects), pick(r, c.owners)
            kind = int(r.integers(9))
            text, q = [
                (
                    f"How many tasks are overdue across all {words['project']}s?",
                    {"op": "count", "entity": "tasks", "where": {"overdue": True}},
                ),
                (
                    f"Which {words['project']}s are {words['at_risk']}?",
                    {"op": "list", "entity": "projects", "where": {"at_risk": True}},
                ),
                (
                    f"How many {words['at_risk']} tasks does {P} have?",
                    {"op": "count", "entity": "tasks", "where": {"project": P, "at_risk": True}},
                ),
                (
                    "Who has the most open tasks due in the next 14 days?",
                    {"op": "top_owner", "entity": "tasks", "where": {"done": False, "due_within_days": 14}},
                ),
                (
                    f"What is the average completion of {P}?",
                    {"op": "avg_progress", "entity": "tasks", "where": {"project": P}},
                ),
                (
                    f"How many {words['milestone']}s are due this quarter?",
                    {"op": "count", "entity": "milestones", "where": {"fiscal_quarter": "current"}},
                ),
                (
                    f"Which {words['milestone']}s are overdue?",
                    {"op": "list", "entity": "milestones", "where": {"overdue": True}},
                ),
                (
                    f"How many tasks in {P} are done?",
                    {"op": "count", "entity": "tasks", "where": {"project": P, "done": True}},
                ),
                (
                    f"How many open tasks does {O} have?",
                    {"op": "count", "entity": "tasks", "where": {"owner": O, "done": False}},
                ),
            ][kind]
            used = [w for w in words.values() if w in UNKNOWN_TERMS]
            out.append({"id": f"{cid}-Q{k + 1:02d}", "customer": cid, "text": text, "query": q, "unknown_terms": used})
        return out
