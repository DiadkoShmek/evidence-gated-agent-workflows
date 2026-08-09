#!/usr/bin/env python3
"""CLI for the isolated local EGOH synthetic demonstration."""

from __future__ import annotations

import argparse
import json
import tempfile
from datetime import datetime
from pathlib import Path

from egoh_demo import JournalOwner, run_scenario


ROOT = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one local synthetic EGOH scenario.")
    parser.add_argument("--scenario", default="valid-review", help="Fixture stem in fixtures/.")
    parser.add_argument(
        "--as-of",
        help="Optional timezone-aware ISO-8601 evaluation time for reproducible fixtures.",
    )
    parser.add_argument(
        "--expect-decision",
        choices=("review-required", "held"),
        help="Exit nonzero unless the evaluated fixture has this exact decision.",
    )
    args = parser.parse_args()
    if not args.scenario or any(character not in "abcdefghijklmnopqrstuvwxyz0123456789-" for character in args.scenario):
        parser.error("scenario must be a lowercase synthetic fixture name")
    fixture = ROOT / "fixtures" / f"{args.scenario}.json"
    as_of = None
    if args.as_of:
        try:
            as_of = datetime.fromisoformat(args.as_of)
        except ValueError:
            parser.error("as-of must be valid ISO-8601")
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            parser.error("as-of must include a timezone offset")
    with tempfile.TemporaryDirectory(prefix="egoh-demo-") as directory:
        result = run_scenario(fixture, JournalOwner(Path(directory)).journal(), now=as_of)
    print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    if args.expect_decision and result["decision"]["decision"] != args.expect_decision:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
