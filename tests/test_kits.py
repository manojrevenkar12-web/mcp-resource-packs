import pytest

from resourcepacks import kits, patterns


def test_wilson_lower_bound():
    assert kits.wilson_lower(60, 60, 1.96) == pytest.approx(0.9398, abs=1e-3)
    assert kits.wilson_lower(0, 0, 1.96) == 0.0
    assert kits.wilson_lower(57, 60, 1.96) > 0.85 > kits.wilson_lower(55, 60, 1.96)


def _kit(cfg, right=60, items=None):
    pack = {
        "sheets": {"1": {"kind": "project", "template": "S"}},
        "templates": {},
        "glossary": {"gate": "milestone"},
        "rules": {
            "at_risk": {"kind": "status"},
            "project_at_risk_share": 0.2,
            "fiscal_start_month": 1,
            "done": "progress",
            "milestone": "flag",
            "summary_rows": "exclude",
        },
        "items": items or [],
        "workflow": {"regulated": False, "tolerance": 0.0},
    }
    result = {"right": right, "questions": 60, "lower": kits.wilson_lower(right, 60, 1.96), "detail": []}
    meta = {"name": "Acme", "sheet_names": {"1": {"name": "Plan"}}}
    files = kits.build(meta, pack, pack, result, {"chosen": "maker_checker", "why": "pilot"}, cfg)
    return files, pack, result


def test_a_finished_kit_passes_the_lint(cfg):
    files, pack, result = _kit(cfg)
    assert kits.lint(files, pack, result, cfg) == []


def test_the_lint_says_why_a_kit_is_not_done(cfg):
    open_item = {
        "id": "role:1:X",
        "kind": "role",
        "key": "X",
        "sheet": "1",
        "value": "status",
        "confidence": 0.5,
        "source": "inferred",
        "evidence": "",
    }
    rule = {
        "id": "rule:-:done",
        "kind": "rule",
        "key": "done",
        "sheet": None,
        "value": "progress",
        "confidence": 0.3,
        "source": "inferred",
        "evidence": "",
    }
    files, pack, result = _kit(cfg, right=50, items=[open_item, rule])
    files["RUNBOOK.md"] += "\n## Step 7. Run the CLI\n\nRun curl against the endpoint.\n"
    problems = " | ".join(kits.lint(files, pack, result, cfg))
    for expected in (
        "curl",
        "endpoint",
        "does not say when it is finished",
        "unconfirmed",
        "workshop: done",
        "lower bound",
    ):
        assert expected in problems


def test_review_questions_read_as_questions():
    q = kits.question_for({"kind": "status_value", "key": "Slipping", "value": "at_risk"}, {})
    assert q == 'When a row\'s status says "Slipping", does that mean at risk?'


def test_patterns_pick_by_compliance_and_tolerance():
    pcfg = {"max_redrafts": 1, "escalation_minutes": 4, "approver_minutes": 1}
    projects = [(f"P{i}", 50) for i in range(40)]
    never = patterns.simulate("single", projects, range(2), lambda *a: False, lambda *a: True, pcfg, lambda n: True)
    assert patterns.choose(True, 0.05, {"single": never})[0] == "maker_checker_approval"
    assert patterns.choose(False, 0.05, {"single": never})[0] == "single"
    assert patterns.choose(False, 0.0, {"single": never})[0] == "maker_checker"


def test_the_checker_turns_slips_into_redrafts_and_escalations():
    pcfg = {"max_redrafts": 1, "escalation_minutes": 4, "approver_minutes": 1}
    projects = [("P", 50)]
    always = lambda *a: True  # noqa: E731
    single = patterns.simulate("single", projects, range(3), always, always, pcfg, lambda n: True)
    mc = patterns.simulate("maker_checker", projects, range(3), always, always, pcfg, lambda n: True)
    assert single.wrong == 3 and mc.wrong == 0 and mc.escalation_minutes == 12 and mc.llm_calls == 6
