"""A local-only polling contract for an asynchronous ComfyUI-style API.

This is deliberately a fake service.  It proves controller behaviour, not
ComfyUI, n8n, a queue, or a network integration.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


class UnknownPromptId(Exception):
    """The upstream service does not recognise the submitted prompt id."""


class TransportCrash(Exception):
    """The poll endpoint crashed before it could return a status."""


TERMINAL_STATES = {"complete", "failed", "crashed", "timed_out", "unknown_id"}


@dataclass(frozen=True)
class PollConfig:
    max_attempts: int = 4
    base_backoff_seconds: int = 1
    timeout_seconds: int = 10

    def __post_init__(self) -> None:
        if self.max_attempts < 1 or self.base_backoff_seconds < 1 or self.timeout_seconds < 1:
            raise ValueError("all polling limits must be positive")


@dataclass
class FakePrompt:
    prompt_id: str
    fingerprint: str
    events: list[Any]
    cursor: int = 0


class FakeComfyUI:
    """Deterministic, in-memory substitute for a ComfyUI async HTTP API.

    Each poll consumes one event from a supplied plan.  Supported events are
    ``queued``, ``running``, ``complete``, ``failed``, ``crashed`` and
    ``transport_crash``.  Reusing a fingerprint returns the same prompt id.
    """

    def __init__(self) -> None:
        self._next_id = 1
        self._by_id: dict[str, FakePrompt] = {}
        self._by_fingerprint: dict[str, str] = {}

    def submit(self, fingerprint: str, events: list[Any]) -> tuple[str, bool]:
        if fingerprint in self._by_fingerprint:
            return self._by_fingerprint[fingerprint], True
        prompt_id = f"fake-prompt-{self._next_id}"
        self._next_id += 1
        self._by_id[prompt_id] = FakePrompt(prompt_id, fingerprint, list(events))
        self._by_fingerprint[fingerprint] = prompt_id
        return prompt_id, False

    def poll(self, prompt_id: str) -> dict[str, Any]:
        prompt = self._by_id.get(prompt_id)
        if prompt is None:
            raise UnknownPromptId(prompt_id)
        event = prompt.events[min(prompt.cursor, len(prompt.events) - 1)] if prompt.events else "queued"
        prompt.cursor += 1
        if event == "transport_crash":
            raise TransportCrash("fake poll endpoint crashed")
        if isinstance(event, dict):
            return event
        if event == "complete":
            return {"state": "complete", "outputs": ["fake-output.png"]}
        if event in {"queued", "running", "failed", "crashed"}:
            return {"state": event}
        raise ValueError(f"unsupported fake event: {event!r}")


@dataclass
class StatusStore:
    """Small JSON persistence surface; one record per idempotency fingerprint."""

    path: Path
    records: dict[str, dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.path.exists():
            self.records = json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, fingerprint: str, record: dict[str, Any]) -> None:
        self.records[fingerprint] = record
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(self.records, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(self.path)


class PollingController:
    """Bounded controller suitable for an n8n poll loop or a worker wrapper."""

    def __init__(
        self,
        service: FakeComfyUI,
        store: StatusStore,
        config: PollConfig = PollConfig(),
        clock: Callable[[], int] | None = None,
    ) -> None:
        self.service = service
        self.store = store
        self.config = config
        self.clock = clock or (lambda: 0)

    def submit_and_poll(self, fingerprint: str, events: list[Any]) -> dict[str, Any]:
        prompt_id, reused = self.service.submit(fingerprint, events)
        started = self.clock()
        attempts = 0
        retry_delays: list[int] = []
        history: list[dict[str, Any]] = []

        while attempts < self.config.max_attempts:
            if self.clock() - started >= self.config.timeout_seconds:
                return self._finish(fingerprint, prompt_id, reused, attempts, retry_delays, history, "timed_out")
            attempts += 1
            try:
                response = self.service.poll(prompt_id)
            except UnknownPromptId:
                return self._finish(fingerprint, prompt_id, reused, attempts, retry_delays, history, "unknown_id")
            except TransportCrash as error:
                history.append({"attempt": attempts, "state": "transport_crash", "detail": str(error)})
                if attempts == self.config.max_attempts:
                    return self._finish(fingerprint, prompt_id, reused, attempts, retry_delays, history, "crashed")
                retry_delays.append(self.config.base_backoff_seconds * (2 ** (attempts - 1)))
                continue

            state = response["state"]
            history.append({"attempt": attempts, "state": state})
            if state == "complete":
                return self._finish(
                    fingerprint, prompt_id, reused, attempts, retry_delays, history, "complete", response.get("outputs", [])
                )
            if state in {"failed", "crashed"}:
                return self._finish(fingerprint, prompt_id, reused, attempts, retry_delays, history, state)
            if state not in {"queued", "running"}:
                return self._finish(fingerprint, prompt_id, reused, attempts, retry_delays, history, "crashed")
            if attempts < self.config.max_attempts:
                retry_delays.append(self.config.base_backoff_seconds * (2 ** (attempts - 1)))

        return self._finish(fingerprint, prompt_id, reused, attempts, retry_delays, history, "timed_out")

    def _finish(
        self,
        fingerprint: str,
        prompt_id: str,
        reused: bool,
        attempts: int,
        retry_delays: list[int],
        history: list[dict[str, Any]],
        state: str,
        outputs: list[str] | None = None,
    ) -> dict[str, Any]:
        if state not in TERMINAL_STATES:
            raise ValueError(f"terminal state required, got {state}")
        record = {
            "fingerprint": fingerprint,
            "prompt_id": prompt_id,
            "reused_submission": reused,
            "state": state,
            "attempts": attempts,
            "retry_delays_seconds": retry_delays,
            "history": history,
            "outputs": outputs or [],
        }
        self.store.save(fingerprint, record)
        return record
