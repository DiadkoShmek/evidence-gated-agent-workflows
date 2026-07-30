"""Run one deterministic happy-path contract demonstration."""

from __future__ import annotations

import json
from pathlib import Path

from contract import FakeComfyUI, PollConfig, PollingController, StatusStore


def main() -> None:
    root = Path(__file__).resolve().parent
    controller = PollingController(
        FakeComfyUI(),
        StatusStore(root / "demo-status.json"),
        PollConfig(max_attempts=4, base_backoff_seconds=1, timeout_seconds=10),
    )
    result = controller.submit_and_poll("creative-asset:campaign-42:v1", ["queued", "running", "complete"])
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
