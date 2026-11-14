"""What the committed dev report must show, so a change that breaks the story fails here."""

import json
from pathlib import Path

R = json.loads((Path(__file__).resolve().parents[1] / "reports" / "dev.json").read_text())


def test_the_kit_beats_reading_raw_sheets_on_accuracy_and_tokens():
    d = R["designs"]
    assert d["kit"]["accuracy"] > d["generic_mcp"]["accuracy"] + 0.4
    assert d["kit"]["tokens_per_question"] * 20 < d["generic_mcp"]["tokens_per_question"]
    assert d["kit"]["customers_accepted"] == d["kit"]["customers"]


def test_every_kit_is_ready_and_no_chosen_pattern_writes_wrong_lines():
    assert R["kits"]["ready"] == R["kits"]["total"]
    assert R["patterns"]["totals"]["chosen"]["wrong"] == 0
    assert R["patterns"]["totals"]["single"]["wrong"] > 0
