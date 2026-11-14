from __future__ import annotations

import os
import tomllib
from pathlib import Path

ROOT = Path(os.environ.get("PACKS_ROOT", Path(__file__).resolve().parents[2]))


def load(name: str) -> dict:
    return tomllib.loads((ROOT / "config" / f"{name}.toml").read_text())
