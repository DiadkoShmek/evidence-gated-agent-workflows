#!/usr/bin/env python3
"""Run a local synthetic publication and emit metadata only."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from immutable_artifact_handoff import publish


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="immutable-artifact-handoff-") as temporary:
        result = publish(Path(temporary), b'{"synthetic":"review-only"}')
        if result.status != "published":
            raise SystemExit(result.reason)
        print(json.dumps({"status": result.status, "reason": result.reason, "handoff": result.handoff}, sort_keys=True))


if __name__ == "__main__":
    main()
