"""Coordination patterns for the one write workflow every customer asks for first: a weekly status line per project
written back to the portfolio sheet.

- single: one agent reads the project's rows and writes the line.
- maker_checker: one agent drafts, a checker recomputes every number with the portfolio engine and the customer's
  pack; a mismatch gets one redraft, then goes to a person.
- maker_checker_approval: as maker_checker, and a person approves every line before it is written, with the audit
  trail a regulated customer needs.

`choose` picks one from what the workshop said (regulated, tolerance) and a pilot week. The checker is what code
decides; the drafting model only writes words around numbers it was given back.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class Outcome:
    lines: int = 0
    wrong: int = 0
    llm_calls: int = 0
    approver_minutes: float = 0.0
    escalation_minutes: float = 0.0
    audit_trail: bool = False
    per_week: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "lines": self.lines,
            "wrong": self.wrong,
            "wrong_rate": round(self.wrong / self.lines, 4) if self.lines else 0.0,
            "llm_calls": self.llm_calls,
            "person_minutes": round(self.approver_minutes + self.escalation_minutes, 1),
            "audit_trail": self.audit_trail,
        }


def simulate(
    pattern: str, projects: list[tuple[str, int]], weeks: range, slips, catches, pcfg: dict, checker_ok
) -> Outcome:
    """Run one pattern over projects (name, rows) and weeks.

    slips(project, rows, week, attempt) -> bool is the drafting model getting the line wrong;
    catches(project, week) -> bool is an approver spotting a wrong line;
    checker_ok(project) -> bool is whether the checker's own numbers are right (they are when the pack is).
    """
    o = Outcome(audit_trail=pattern == "maker_checker_approval")
    for wk in weeks:
        for name, rows in projects:
            o.lines += 1
            o.llm_calls += 1
            wrong = slips(name, rows, wk, 0)
            if pattern != "single":
                attempt = 0
                while wrong and attempt < pcfg["max_redrafts"]:
                    attempt += 1
                    o.llm_calls += 1
                    wrong = slips(name, rows, wk, attempt)
                if wrong:
                    o.escalation_minutes += pcfg["escalation_minutes"]
                    wrong = False
                if not checker_ok(name):
                    wrong = True
            if pattern == "maker_checker_approval":
                o.approver_minutes += pcfg["approver_minutes"]
                if wrong and catches(name, wk):
                    wrong = False
            o.wrong += int(wrong)
    return o


def upper(k: int, n: int, z: float = 1.645) -> float:
    """One-sided 95% Wilson upper bound on a rate seen k times in n."""
    if n == 0:
        return 1.0
    p = k / n
    d = 1 + z * z / n
    return (p + z * z / (2 * n) + z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d


def choose(regulated: bool, tolerance: float, pilot: dict[str, Outcome]) -> tuple[str, str]:
    """The cheapest pattern the pilot shows is within the customer's tolerance, at 95% confidence."""
    if regulated:
        return "maker_checker_approval", "regulated, so a person approves every line and the trail is kept"
    single = pilot["single"]
    ub = upper(single.wrong, single.lines)
    if ub <= tolerance:
        return (
            "single",
            f"one agent alone: at most {ub:.1%} of lines wrong at 95% confidence, within the {tolerance:.0%} accepted",
        )
    return "maker_checker", (
        f"one agent alone was wrong on {single.wrong} of {single.lines} pilot lines; at 95% confidence that could be "
        f"{ub:.0%}, above the {tolerance:.0%} the customer accepts"
    )
