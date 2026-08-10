#!/usr/bin/env python3
"""Run the checked-in composed operating-core fixture in an ephemeral directory."""

from __future__ import annotations

import json
from pathlib import Path

from operating_core_demo import run_boundary


ROOT = Path(__file__).resolve().parent


def main() -> int:
    boundary = json.loads((ROOT / "fixtures" / "clean-complete.json").read_text(encoding="utf-8"))
    result = run_boundary(boundary)
    print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    return 0 if result["decision"] == "review-required" else 2


if __name__ == "__main__":
    raise SystemExit(main())
