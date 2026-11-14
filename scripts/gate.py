"""Fails (exit 1) when reports/dev.json does not clear config/gate.toml."""

from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check(r: dict, g: dict) -> list[str]:
    d = r["designs"]
    k, raw = d["kit"], d["generic_mcp"]
    out = []
    if k["accuracy"] < g["kit"]["min_accuracy"]:
        out.append(f"kit accuracy {k['accuracy']:.3f} < {g['kit']['min_accuracy']}")
    if k["customers_accepted"] < g["kit"]["min_customers_accepted_share"] * k["customers"]:
        out.append(f"only {k['customers_accepted']} of {k['customers']} customers accepted")
    if k["tokens_per_question"] > g["kit"]["max_tokens_per_question"]:
        out.append(f"{k['tokens_per_question']} tokens per question")
    if k["accuracy"] - raw["accuracy"] < g["versus_raw_sheets"]["min_accuracy_gain"]:
        out.append("the kit is not far enough ahead of raw sheets")
    if raw["tokens_per_question"] < g["versus_raw_sheets"]["min_token_ratio"] * k["tokens_per_question"]:
        out.append("the kit does not save enough tokens")
    per = r["volume"]["review_items"] / r["volume"]["customers"]
    if per > g["inference"]["max_review_items_per_customer"]:
        out.append(f"{per:.1f} review questions per customer")
    if r["patterns"]["totals"]["chosen"]["wrong"] > g["writes"]["max_wrong_lines_chosen"]:
        out.append(f"{r['patterns']['totals']['chosen']['wrong']} wrong status lines from the chosen patterns")
    if r["kits"]["ready"] < g["kits"]["min_ready_share"] * r["kits"]["total"]:
        out.append(f"{r['kits']['ready']} of {r['kits']['total']} kits ready")
    return out


def main() -> None:
    r = json.loads((ROOT / "reports" / "dev.json").read_text())
    g = tomllib.loads((ROOT / "config" / "gate.toml").read_text())
    problems = check(r, g)
    for p in problems:
        print("GATE:", p)
    if problems:
        sys.exit(1)
    print("Gate passed.")


if __name__ == "__main__":
    main()
