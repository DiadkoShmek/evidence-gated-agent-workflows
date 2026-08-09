"""Run one deterministic happy-path contract demonstration."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile

from contract import FakeComfyUI, PollConfig, PollingController, StatusStore


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="async-polling-demo-") as directory:
        controller = PollingController(
            FakeComfyUI(),
            StatusStore(Path(directory) / "status.json"),
            PollConfig(max_attempts=4, base_backoff_seconds=1, timeout_seconds=10),
        )
        result = controller.submit_and_poll(
            "creative-asset:campaign-42:v1", ["queued", "running", "complete"]
        )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
