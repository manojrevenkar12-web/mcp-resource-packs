"""Reads a customer's workspace and drafts its resource pack, with a confidence and the evidence for every decision.

Nothing here is configured by hand per customer. Sheets with the same columns share a template; each template's
columns get roles from their titles (the base lexicon) and from their values (types, ranges, which date is always the
later one, what a ticked box coincides with). Status values are mapped by the lexicon, then by picklist order. Every
decision below the review threshold becomes a question for the customer's admin; rules no sheet can show (what "at
risk" means here, the fiscal year, what counts as done) are left at defaults and marked for the workshop.
"""

from __future__ import annotations

import hashlib
import re
from datetime import date

from . import lexicon
from .engine import parse_date

DMY = re.compile(r"^\d{1,2}\.\d{1,2}\.\d{4}$")


def signature(sheet: dict) -> str:
    titles = "|".join(sorted(c["title"] for c in sheet["columns"]))
    return "S" + hashlib.blake2b(titles.encode(), digest_size=3).hexdigest()


def _values(sheets: list[dict], col_title: str) -> list:
    out = []
    for s in sheets:
        cid = next(c["id"] for c in s["columns"] if c["title"] == col_title)
        for r in s["rows"]:
            for cell in r["cells"]:
                if cell["columnId"] == cid and cell["value"] not in (None, ""):
                    out.append(cell["value"])
    return out


def _is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _date_format(col: dict, vals: list) -> str | None:
    if col["type"] == "DATE":
        return "iso"
    if vals and all(isinstance(v, str) and DMY.match(v) for v in vals):
        return "dmy_text"
    return None


def _progress_format(vals: list) -> str | None:
    if not vals:
        return None
    if all(isinstance(v, str) and re.fullmatch(r"\s*\d+(?:[.,]\d+)?\s*%\s*", v) for v in vals):
        return "percent_text"
    if all(_is_number(v) for v in vals):
        if all(0 <= v <= 1 for v in vals):
            return "fraction"
        if all(0 <= v <= 100 for v in vals) and any(v > 1 for v in vals):
            return "percent"
    return None


class Drafter:
    def __init__(self, cfg: dict, today: date):
        self.cfg = cfg
        self.today = today
        self.items: list[dict] = []

    def item(self, kind: str, key: str, value, confidence: float, evidence: str, sheet: str | None = None) -> None:
        self.items.append(
            {
                "id": f"{kind}:{sheet or '-'}:{key}",
                "kind": kind,
                "key": key,
                "sheet": sheet,
                "value": value,
                "confidence": round(confidence, 2),
                "evidence": evidence,
                "source": "inferred",
            }
        )

    # ------------------------------------------------------------------------------------------ sheets

    def sheet_kind(self, s: dict) -> tuple[str, float, str]:
        if re.search(lexicon.ARCHIVE_PATTERN, s["name"]):
            return "archive", 0.95, "the name says it is archived"
        dateish = [c for c in s["columns"] if _date_format(c, _values([s], c["title"])[:30])]
        numeric = [c for c in s["columns"] if _progress_format(_values([s], c["title"]))]
        if len(dateish) < 2 or not (numeric or any(c["type"] == "PICKLIST" for c in s["columns"])):
            return "other", 0.9, f"{len(dateish)} date column(s), no plan shape: not a project plan"
        latest = []
        for c in dateish:
            fmt = _date_format(c, _values([s], c["title"])[:30])
            latest += [d for d in (parse_date(v, fmt) for v in _values([s], c["title"])) if d]
        if latest and max(latest) < self.today.replace(year=self.today.year - 1):
            return "archive", 0.6, f"nothing dated after {max(latest).isoformat()}: probably finished"
        return "project", 0.9, f"{len(s['rows'])} rows with start and end dates"

    # ------------------------------------------------------------------------------------------ one template

    def template(self, sig: str, sheets: list[dict]) -> dict:
        rep = str(sheets[0]["id"])
        cols = sheets[0]["columns"]
        roles: dict[str, str] = {}
        conf: dict[str, tuple[float, str]] = {}

        def put(role: str, title: str, c: float, why: str) -> None:
            if role not in roles or c > conf[role][0]:
                roles[role] = title
                conf[role] = (c, why)

        primary = next((c for c in cols if c.get("primary")), cols[0])
        put("task", primary["title"], 1.0, "primary column")
        dates, fmts = [], {}
        for c in cols:
            vals = _values(sheets, c["title"])
            fmt = _date_format(c, vals)
            if fmt:
                dates.append(c)
                fmts[c["title"]] = fmt
        # dates: titles first, then which one is always the later
        named = {lexicon.role_for_title(c["title"]): c for c in dates}
        if "start" in named and "due" in named:
            put("start", named["start"]["title"], 0.95, "title")
            put("due", named["due"]["title"], 0.95, "title")
        elif len(dates) >= 2:
            a, b = dates[0], dates[1]
            pairs = self._paired(sheets, a, b, fmts)
            later = sum(1 for x, y in pairs if y >= x) / max(1, len(pairs))
            first, second = (a, b) if later >= 0.5 else (b, a)
            share = max(later, 1 - later)
            put("start", first["title"], 0.85 if share > 0.97 else 0.6, f"earlier date in {share:.0%} of rows")
            put("due", second["title"], 0.85 if share > 0.97 else 0.6, f"later date in {share:.0%} of rows")
        date_fmt = fmts.get(roles.get("due", ""), "iso")
        for c in cols:
            if c is primary or c in dates:
                continue
            by_title = lexicon.role_for_title(c["title"])
            vals = _values(sheets, c["title"])
            if c["type"] == "PICKLIST":
                opts = c.get("options") or sorted({str(v) for v in vals})
                known = sum(1 for o in opts if lexicon.status_for_value(o))
                if by_title == "status":
                    put("status", c["title"], 0.95, "title")
                elif known >= 2:
                    put("status", c["title"], 0.85, f"{known} of {len(opts)} values are status words")
                elif len(opts) in (3, 4):
                    put("status", c["title"], 0.55, f"a {len(opts)}-value picklist")
            elif c["type"] == "CONTACT_LIST":
                put("owner", c["title"], 0.95 if by_title == "owner" else 0.85, "contact column")
            elif c["type"] == "CHECKBOX":
                if by_title in ("done", "milestone"):
                    put(by_title, c["title"], 0.95, "title")
                else:
                    role, c2, why = self._checkbox(sheets, c, roles, fmts)
                    if role:
                        put(role, c["title"], c2, why)
            else:
                pf = _progress_format(vals)
                if pf:
                    if by_title == "progress":
                        put("progress", c["title"], 0.95, f"title, values look like {pf}")
                    elif not any(w in c["title"].lower() for w in ("budget", "capacity", "cost")):
                        put("progress", c["title"], 0.65, f"values look like {pf}")
        for role, title in roles.items():
            c, why = conf[role]
            self.item("role", title, role, c, why, rep)
        out = {"roles": roles, "status_values": {}, "progress": "fraction", "dates": date_fmt}
        if "progress" in roles:
            out["progress"] = _progress_format(_values(sheets, roles["progress"])) or "fraction"
            self.item("progress", roles["progress"], out["progress"], 0.9, "value range", rep)
        if date_fmt != "iso":
            self.item("dates", roles["due"], date_fmt, 0.7, "dates written as text", rep)
        if "status" in roles:
            col = next(c for c in cols if c["title"] == roles["status"])
            opts = col.get("options") or sorted({str(v) for v in _values(sheets, roles["status"])})
            mapped = {o: lexicon.status_for_value(o) for o in opts}
            free = [x for x in ("on_track", "at_risk", "off_track") if x not in mapped.values()]
            for o in opts:
                if mapped[o]:
                    self.item("status_value", o, mapped[o], 0.95, "status word", rep)
                elif free:
                    # picklists usually run from good to bad
                    guess = free.pop(0)
                    mapped[o] = guess
                    self.item(
                        "status_value", o, guess, 0.5, "not a known status word; guessed from picklist order", rep
                    )
            out["status_values"] = {o: v for o, v in mapped.items() if v}
        return out

    def _paired(self, sheets, a, b, fmts):
        pairs = []
        for s in sheets:
            ia = next(c["id"] for c in s["columns"] if c["title"] == a["title"])
            ib = next(c["id"] for c in s["columns"] if c["title"] == b["title"])
            for r in s["rows"]:
                v = {cell["columnId"]: cell["value"] for cell in r["cells"]}
                x, y = parse_date(v.get(ia), fmts[a["title"]]), parse_date(v.get(ib), fmts[b["title"]])
                if x and y:
                    pairs.append((x, y))
        return pairs

    def _checkbox(self, sheets, col, roles, fmts):
        """A tick box nobody named in a way we know: a milestone flag if ticked rows have no duration, a done flag
        if ticked rows are (nearly) complete."""
        if "start" not in roles or "due" not in roles:
            return None, 0, ""
        zero = high = ticked = 0
        for s in sheets:
            ids = {c["title"]: c["id"] for c in s["columns"]}
            for r in s["rows"]:
                v = {cell["columnId"]: cell["value"] for cell in r["cells"]}
                if not v.get(ids[col["title"]]):
                    continue
                ticked += 1
                st = parse_date(v.get(ids[roles["start"]]), fmts[roles["start"]])
                du = parse_date(v.get(ids[roles["due"]]), fmts[roles["due"]])
                zero += int(st is not None and st == du)
                if "progress" in roles:
                    p = v.get(ids[roles["progress"]])
                    high += int(isinstance(p, (int, float)) and p >= 0.7 * (100 if p > 1 else 1))
        if not ticked:
            return None, 0, ""
        if zero / ticked > 0.9:
            return "milestone", 0.85, f"{zero} of {ticked} ticked rows have no duration"
        if high / ticked > 0.9:
            return "done", 0.75, f"{high} of {ticked} ticked rows are at least 70% complete"
        return None, 0, ""


def draft(workspace: dict, cfg: dict, today: date) -> dict:
    """The pack as inference alone writes it: every decision with its confidence, rules at their defaults."""
    d = Drafter(cfg, today)
    sheets_meta, groups = {}, {}
    for s in workspace["sheets"]:
        kind, c, why = d.sheet_kind(s)
        d.item("sheet_kind", str(s["id"]), kind, c, f"{s['name']}: {why}", str(s["id"]))
        sig = signature(s)
        sheets_meta[str(s["id"])] = {"kind": kind, "template": sig}
        groups.setdefault(sig, []).append(s)
    templates = {}
    for sig, sheets in groups.items():
        if any(sheets_meta[str(s["id"])]["kind"] != "other" for s in sheets):
            plan = [s for s in sheets if sheets_meta[str(s["id"])]["kind"] == "project"] or sheets
            templates[sig] = d.template(sig, plan)
    roles_seen = {r for t in templates.values() for r in t["roles"]}
    rules = {
        "at_risk": {"kind": "status"},
        "fiscal_start_month": 1,
        "done": "checkbox" if "done" in roles_seen else "progress",
        "milestone": "flag" if "milestone" in roles_seen else "zero_duration",
        "summary_rows": "exclude",
        "project_at_risk_share": cfg["defaults"]["project_at_risk_share"],
    }
    for k in ("at_risk", "fiscal_start_month", "done", "project_at_risk_share"):
        d.item("rule", k, rules[k], 0.3, "no sheet can show this; ask in the workshop")
    return {
        "customer": workspace["customer"],
        "sheets": sheets_meta,
        "templates": templates,
        "rules": rules,
        "glossary": {},
        "items": d.items,
    }
