from datetime import date

from hypothesis import given
from hypothesis import strategies as st

from resourcepacks import engine


def test_the_truth_pack_reads_every_task_the_world_wrote(world):
    for c in world.customers[:4]:
        ws, truth = world.workspace(c.id), world.truth_pack(c.id)
        rows = engine.tasks(ws, truth)
        live = [s for s in ws["sheets"] if c.kinds[s["id"]] == "project"]
        phases = sum(1 for s in live for r in s["rows"] if any(x.get("parentId") == r["id"] for x in s["rows"]))
        assert len(rows) == sum(len(s["rows"]) for s in live) - phases
        assert all(x["status"] in ("on_track", "at_risk", "off_track") for x in rows)
        assert all(x["start"] and x["due"] and x["start"] <= x["due"] for x in rows)
        assert all(0 <= x["progress"] <= 1 for x in rows)


@given(st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31)), st.integers(1, 12))
def test_every_day_is_in_one_fiscal_quarter_and_quarters_are_three_months(d, start):
    y, q = engine.fiscal_quarter(d, start)
    assert 1 <= q <= 4
    first = date(d.year if d.month >= start else d.year - 1, start, 1)
    months = (d.year - first.year) * 12 + d.month - first.month
    assert q == months // 3 + 1


def test_progress_and_dates_in_every_format():
    assert engine.parse_progress(0.45, "fraction") == 0.45
    assert engine.parse_progress(45, "percent") == 0.45
    assert engine.parse_progress("45 %", "percent_text") == 0.45
    assert engine.parse_progress("12,5%", "percent_text") == 0.125
    assert engine.parse_date("16.11.2026", "dmy_text") == date(2026, 11, 16)
    assert engine.parse_date("2026-11-16", "iso") == date(2026, 11, 16)
    assert engine.parse_date("soon", "iso") is None


def test_at_risk_follows_the_customers_rule():
    today = date(2026, 11, 16)
    x = {"done": False, "status": "on_track", "due": date(2026, 11, 20), "progress": 0.5}
    assert not engine.at_risk(x, {"at_risk": {"kind": "status"}}, today)
    assert engine.at_risk(x, {"at_risk": {"kind": "status_or_due_soon", "days": 7, "below": 0.8}}, today)
    assert not engine.at_risk(dict(x, done=True, status="off_track"), {"at_risk": {"kind": "status"}}, today)


def test_an_average_matches_within_half_a_point():
    assert engine.same(31.6, 31.9) and not engine.same(31.6, 32.2)
    assert engine.same(["a"], ["a"]) and not engine.same(3, 4)
