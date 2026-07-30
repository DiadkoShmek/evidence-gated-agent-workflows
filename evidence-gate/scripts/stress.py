#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evidence_gate import canonical_json, evaluate  # noqa: E402


EXPECTED = {
    "clean": "draft",
    "missing": "hold",
    "conflict": "hold",
    "stale": "hold",
    "risk": "escalate",
}
AS_OF = "2026-07-30T12:00:00Z"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=1000)
    parser.add_argument("--max-seconds", type=float, default=10.0)
    args = parser.parse_args()
    if not 1 <= args.iterations <= 100_000:
        raise SystemExit("iterations must be in 1..100000")
    if not 0.1 <= args.max_seconds <= 60.0:
        raise SystemExit("max-seconds must be in 0.1..60")

    fixtures = {
        name: json.loads((ROOT / "fixtures" / f"{name}.json").read_text(encoding="utf-8"))
        for name in EXPECTED
    }
    baseline = {name: evaluate(raw, AS_OF) for name, raw in fixtures.items()}
    start = time.monotonic()
    digest = hashlib.sha256()
    runs = 0
    for _ in range(args.iterations):
        for name, raw in fixtures.items():
            result = evaluate(raw, AS_OF)
            if result != baseline[name] or result["decision"] != EXPECTED[name]:
                raise SystemExit(f"decision drift in {name}")
            digest.update(canonical_json(result).encode("utf-8"))
            runs += 1
        if time.monotonic() - start > args.max_seconds:
            raise SystemExit("stress time budget exceeded")

    elapsed = time.monotonic() - start
    print(
        json.dumps(
            {
                "status": "PASS",
                "fixture_families": len(fixtures),
                "iterations": args.iterations,
                "evaluation_runs": runs,
                "elapsed_seconds": round(elapsed, 6),
                "trace_digest": digest.hexdigest(),
                "network_access_performed": False,
                "external_action_performed": False,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
