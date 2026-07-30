from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from contract import FakeComfyUI, PollConfig, PollingController, StatusStore


class TickClock:
    def __init__(self, ticks: list[int]) -> None:
        self.ticks = iter(ticks)

    def __call__(self) -> int:
        return next(self.ticks)


class PollingContractTests(unittest.TestCase):
    def controller(self, clock=None):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "status.json"
        return PollingController(FakeComfyUI(), StatusStore(path), PollConfig(max_attempts=4, base_backoff_seconds=2, timeout_seconds=10), clock), path

    def test_complete_persists_and_reuses_fingerprint(self) -> None:
        controller, path = self.controller()
        first = controller.submit_and_poll("same-input", ["queued", "running", "complete"])
        second = controller.submit_and_poll("same-input", ["complete"])
        self.assertEqual(first["state"], "complete")
        self.assertEqual(first["retry_delays_seconds"], [2, 4])
        self.assertTrue(second["reused_submission"])
        self.assertEqual(second["prompt_id"], first["prompt_id"])
        stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(stored["same-input"]["state"], "complete")

    def test_transport_crashes_are_bounded_with_exponential_backoff(self) -> None:
        controller, _ = self.controller()
        result = controller.submit_and_poll("crash", ["transport_crash"])
        self.assertEqual(result["state"], "crashed")
        self.assertEqual(result["attempts"], 4)
        self.assertEqual(result["retry_delays_seconds"], [2, 4, 8])

    def test_unknown_id_is_a_terminal_failure(self) -> None:
        controller, _ = self.controller()
        prompt_id, _ = controller.service.submit("known", ["queued"])
        del controller.service._by_id[prompt_id]
        result = controller.submit_and_poll("known", ["queued"])
        self.assertEqual(result["state"], "unknown_id")
        self.assertEqual(result["attempts"], 1)

    def test_timeout_stops_before_a_poll(self) -> None:
        controller, _ = self.controller(TickClock([0, 10]))
        result = controller.submit_and_poll("slow", ["queued"])
        self.assertEqual(result["state"], "timed_out")
        self.assertEqual(result["attempts"], 0)

    def test_explicit_upstream_failure_is_not_retried(self) -> None:
        controller, _ = self.controller()
        result = controller.submit_and_poll("failed", ["failed"])
        self.assertEqual(result["state"], "failed")
        self.assertEqual(result["retry_delays_seconds"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
