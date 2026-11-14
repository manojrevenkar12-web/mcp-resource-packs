"""The invariants in AGENTS.md, checked."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVING = ["engine.py", "infer.py", "review.py", "kits.py", "patterns.py", "lexicon.py", "settings.py"]


def test_nothing_that_serves_reads_the_truth():
    for name in SERVING:
        src = (ROOT / "src" / "resourcepacks" / name).read_text()
        assert not re.search(r"\bworld\b|truth_pack|admin_answer", src.split('"""', 2)[-1]), name
    for p in (ROOT / "server" / "src").glob("*.ts"):
        assert "world" not in p.read_text().lower(), p.name


def test_only_the_evaluation_export_and_tests_import_the_world():
    for p in (ROOT / "scripts").glob("*.py"):
        if "resourcepacks.world" in p.read_text():
            assert p.name in ("evaluate.py", "export.py"), p.name


def test_the_world_does_not_read_the_packs_settings():
    for p in (ROOT / "src" / "resourcepacks" / "world").glob("*.py"):
        assert 'load("packs")' not in p.read_text() and "packs.toml" not in p.read_text(), p.name


def test_the_heldout_world_builds_and_differs(world):
    from resourcepacks.settings import load
    from resourcepacks.world.sim import World

    h = World(load("heldout"))
    assert {c.lang for c in h.customers} - {c.lang for c in world.customers}
    assert h.customers[0].sheets[0]["name"] != world.customers[0].sheets[0]["name"]
