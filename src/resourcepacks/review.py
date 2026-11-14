"""Turns a drafted pack into the one a customer signs off: admin answers for the uncertain decisions, workshop
answers for the rules no sheet can show."""

from __future__ import annotations

import copy
from collections.abc import Callable


def queue(pack: dict, threshold: float) -> list[dict]:
    """Decisions a consultant must confirm with the customer's admin, worst first."""
    return sorted(
        (i for i in pack["items"] if i["kind"] != "rule" and i["confidence"] < threshold),
        key=lambda i: (i["confidence"], i["id"]),
    )


def apply_admin(pack: dict, threshold: float, ask: Callable[[dict], object]) -> tuple[dict, int]:
    """Ask the admin about every queued decision and write the answers in. Returns the pack and how many were asked."""
    p = copy.deepcopy(pack)
    asked = queue(p, threshold)
    for it in asked:
        ans = ask(it)
        sheet = it["sheet"]
        if it["kind"] == "sheet_kind":
            p["sheets"][it["key"]]["kind"] = ans
            if ans != "other":
                sig = p["sheets"][it["key"]]["template"]
                p["templates"].setdefault(
                    sig, {"roles": {}, "status_values": {}, "progress": "fraction", "dates": "iso"}
                )
        else:
            t = p["templates"][p["sheets"][sheet]["template"]]
            if it["kind"] == "role":
                t["roles"] = {r: c for r, c in t["roles"].items() if c != it["key"] and r != ans}
                if ans:
                    t["roles"][ans] = it["key"]
            elif it["kind"] == "status_value":
                if ans:
                    t["status_values"][it["key"]] = ans
                else:
                    t["status_values"].pop(it["key"], None)
            elif it["kind"] == "progress":
                t["progress"] = ans
            elif it["kind"] == "dates":
                t["dates"] = ans
        for x in p["items"]:
            if x["id"] == it["id"]:
                x.update(value=ans, confidence=1.0, source="admin")
    return p, len(asked)


def apply_workshop(pack: dict, answers: dict) -> dict:
    p = copy.deepcopy(pack)
    p["rules"].update(answers["rules"])
    p["glossary"] = dict(answers["glossary"])
    for x in p["items"]:
        if x["kind"] == "rule":
            x.update(value=p["rules"][x["key"]], confidence=1.0, source="workshop")
    p["workflow"] = {"regulated": answers["regulated"], "tolerance": answers["tolerance"]}
    return p
