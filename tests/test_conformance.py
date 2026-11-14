"""The fixture the TypeScript engine is tested against still holds the Python engine's answers."""

import json
from datetime import date
from pathlib import Path

from resourcepacks import engine

FIX = Path(__file__).resolve().parents[1] / "server" / "test" / "fixtures" / "conformance.json"


def test_python_engine_reproduces_the_fixture():
    f = json.loads(FIX.read_text())
    today = date.fromisoformat(f["today"])
    for c in f["cases"]:
        ws = f["workspaces"][c["variant"].split(":")[0]]
        assert engine.same(engine.answer(ws, f["packs"][c["variant"]], c["query"], today), c["answer"]), c
