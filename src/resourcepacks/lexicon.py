"""What the product already knows about how people name things in a Smartsheet project plan.

This is the base vocabulary every pack starts from, kept as data. Field findings (`scripts/findings.py`) propose
additions when the same title or value goes to review at several customers.
"""

ROLE_WORDS = {
    "task": ["task", "task name", "activity", "aufgabe"],
    "status": ["status", "rag", "health", "project health", "ampel"],
    "progress": ["% complete", "progress", "percent complete", "fortschritt"],
    "start": ["start", "start date", "beginn"],
    "due": ["end date", "finish", "due date", "due", "ende", "enddatum", "end"],
    "owner": ["assigned to", "owner", "responsible", "verantwortlich"],
    "done": ["done", "complete?", "erledigt"],
    "milestone": ["milestone", "meilenstein"],
}

STATUS_WORDS = {
    "on_track": ["green", "on track", "g", "grün"],
    "at_risk": ["yellow", "amber", "at risk", "a", "gelb"],
    "off_track": ["red", "off track", "r", "rot", "blocked"],
}

ARCHIVE_PATTERN = r"(?i)\barchiv|\(old\)|^zz_|\[closed\]|\babgeschlossen\b"


def role_for_title(title: str) -> str | None:
    t = title.strip().lower()
    for role, words in ROLE_WORDS.items():
        if t in words:
            return role
    return None


def status_for_value(value: str) -> str | None:
    v = str(value).strip().lower()
    for canon, words in STATUS_WORDS.items():
        if v in words:
            return canon
    return None
