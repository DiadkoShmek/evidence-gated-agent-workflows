#!/usr/bin/env python3
"""CLI for the isolated local EGOH synthetic demonstration."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from egoh_demo import JournalOwner, run_scenario


ROOT = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one local synthetic EGOH scenario.")
    parser.add_argument("--scenario", default="valid-review", help="Fixture stem in fixtures/.")
    args = parser.parse_args()
    if not args.scenario or any(character not in "abcdefghijklmnopqrstuvwxyz0123456789-" for character in args.scenario):
        parser.error("scenario must be a lowercase synthetic fixture name")
    fixture = ROOT / "fixtures" / f"{args.scenario}.json"
    with tempfile.TemporaryDirectory(prefix="egoh-demo-") as directory:
        result = run_scenario(fixture, JournalOwner(Path(directory)).journal())
    print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
