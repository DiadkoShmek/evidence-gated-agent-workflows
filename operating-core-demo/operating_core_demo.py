"""Local-only composition of the three checked-in synthetic owner contracts.

This module deliberately adds no transport, provider, browser, or production
surface.  It binds one frozen synthetic boundary to the existing evidence gate,
bounded fake lifecycle, and EGOH handoff APIs.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
for owner_path in (ROOT / "evidence-gate" / "src", ROOT / "async-polling-contract", ROOT / "egoh-demo"):
    owner_text = str(owner_path)
    if owner_text not in sys.path:
        sys.path.insert(0, owner_text)

from contract import FakeComfyUI, PollConfig, PollingController, StatusStore  # noqa: E402
from egoh_demo import (  # noqa: E402
    JournalOwner,
    ValidationError,
    build_handoff,
    decide as decide_egoh,
    parse_utc,
    record_decision,
    validate_scenario,
    zero_effect_counters,
)
from evidence_gate import ContractError, content_hash, evaluate, require_identifier  # noqa: E402


BOUNDARY_SCHEMA = "operating-core-demo-boundary-v1"
RESULT_SCHEMA = "operating-core-demo-result-v1"
BOUNDARY_KEYS = {
    "schema",
    "chain_id",
    "as_of",
    "evidence",
    "evidence_sha256",
    "lifecycle",
    "egoh_observation",
}
LIFECYCLE_KEYS = {"fingerprint", "events", "max_attempts", "base_backoff_seconds", "timeout_seconds"}
ALLOWED_FAKE_EVENTS = frozenset({"queued", "running", "complete", "failed", "crashed", "transport_crash"})


class BoundaryError(ValueError):
    """Stable, content-free reason for a malformed synthetic boundary."""


def _strict_int(value: object, *, minimum: int, maximum: int, reason: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise BoundaryError(reason)
    return value


def _validate_boundary(value: object) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != BOUNDARY_KEYS:
        raise BoundaryError("boundary-schema-invalid")
    if value["schema"] != BOUNDARY_SCHEMA:
        raise BoundaryError("boundary-schema-unsupported")
    try:
        chain_id = require_identifier(value["chain_id"], "chain_id")
    except ContractError as exc:
        raise BoundaryError("boundary-chain-id-invalid") from exc
    if not isinstance(value["as_of"], str):
        raise BoundaryError("boundary-as-of-invalid")
    try:
        parse_utc(value["as_of"])
    except ValidationError as exc:
        raise BoundaryError("boundary-as-of-invalid") from exc
    if not isinstance(value["evidence_sha256"], str) or value["evidence_sha256"] != content_hash(value["evidence"]):
        raise BoundaryError("boundary-evidence-digest-invalid")
    if not isinstance(value["evidence"], dict) or value["evidence"].get("case_id") != chain_id:
        raise BoundaryError("boundary-evidence-identity-invalid")

    lifecycle = value["lifecycle"]
    if not isinstance(lifecycle, dict) or set(lifecycle) != LIFECYCLE_KEYS:
        raise BoundaryError("boundary-lifecycle-schema-invalid")
    expected_fingerprint = f"operating-core:{chain_id}:{value['evidence_sha256']}"
    if lifecycle["fingerprint"] != expected_fingerprint:
        raise BoundaryError("boundary-lifecycle-identity-invalid")
    events = lifecycle["events"]
    if not isinstance(events, list) or not 1 <= len(events) <= 4 or any(event not in ALLOWED_FAKE_EVENTS for event in events):
        raise BoundaryError("boundary-lifecycle-events-invalid")
    _strict_int(lifecycle["max_attempts"], minimum=1, maximum=4, reason="boundary-lifecycle-limits-invalid")
    _strict_int(lifecycle["base_backoff_seconds"], minimum=1, maximum=10, reason="boundary-lifecycle-limits-invalid")
    _strict_int(lifecycle["timeout_seconds"], minimum=1, maximum=60, reason="boundary-lifecycle-limits-invalid")

    try:
        observation = validate_scenario(value["egoh_observation"])
    except ValidationError as exc:
        raise BoundaryError("boundary-egoh-observation-invalid") from exc
    if observation["scenario_id"] != chain_id:
        raise BoundaryError("boundary-egoh-identity-invalid")
    return value


def _result(
    *,
    chain_id: str,
    decision: str,
    reason: str,
    evidence_decision: dict[str, Any] | None,
    lifecycle: dict[str, Any] | None,
    egoh: dict[str, Any] | None,
    handoff: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "schema": RESULT_SCHEMA,
        "chain_id": chain_id,
        "decision": decision,
        "reason": reason,
        "evidence_decision": evidence_decision,
        "lifecycle": lifecycle,
        "egoh": egoh,
        "handoff": handoff,
        "effect_counters": zero_effect_counters(),
        "authority": False,
        "external_action": False,
        "provider": False,
        "provider_delivery_observed": False,
        "production": False,
    }


def _run_boundary_in_directory(
    boundary_value: object,
    output_root: Path,
    *,
    clock: Callable[[], int] | None = None,
) -> dict[str, Any]:
    """Private test seam for one bounded run beneath an exact temporary root.

    Only an exact evidence ``draft`` enters the existing lifecycle controller.
    Only its exact terminal ``complete`` reaches the existing EGOH decision and
    local journal owner. It is intentionally private: the public API below
    owns the ephemeral directory and exposes no output-path selection.
    """
    chain_id = boundary_value.get("chain_id", "unknown") if isinstance(boundary_value, dict) else "unknown"
    if not isinstance(chain_id, str):
        chain_id = "unknown"
    try:
        boundary = _validate_boundary(boundary_value)
    except BoundaryError as exc:
        return _result(
            chain_id=chain_id,
            decision="held",
            reason=str(exc),
            evidence_decision=None,
            lifecycle=None,
            egoh=None,
            handoff=None,
        )

    evidence_decision = evaluate(boundary["evidence"], boundary["as_of"])
    if evidence_decision["decision"] != "draft":
        return _result(
            chain_id=boundary["chain_id"],
            decision="held",
            reason="evidence-not-draft",
            evidence_decision=evidence_decision,
            lifecycle=None,
            egoh=None,
            handoff=None,
        )

    lifecycle_input = boundary["lifecycle"]
    controller = PollingController(
        FakeComfyUI(),
        StatusStore(output_root / "synthetic-status.json"),
        PollConfig(
            max_attempts=lifecycle_input["max_attempts"],
            base_backoff_seconds=lifecycle_input["base_backoff_seconds"],
            timeout_seconds=lifecycle_input["timeout_seconds"],
        ),
        clock,
    )
    lifecycle = controller.submit_and_poll(lifecycle_input["fingerprint"], lifecycle_input["events"])
    if lifecycle["state"] != "complete":
        return _result(
            chain_id=boundary["chain_id"],
            decision="held",
            reason="lifecycle-not-complete",
            evidence_decision=evidence_decision,
            lifecycle=lifecycle,
            egoh=None,
            handoff=None,
        )

    egoh_decision = decide_egoh(boundary["egoh_observation"], now=parse_utc(boundary["as_of"]))
    if egoh_decision["decision"] != "review-required":
        return _result(
            chain_id=boundary["chain_id"],
            decision="held",
            reason="egoh-not-review-required",
            evidence_decision=evidence_decision,
            lifecycle=lifecycle,
            egoh={"decision": egoh_decision, "journal": None},
            handoff=None,
        )
    try:
        event, replayed = record_decision(JournalOwner(output_root).journal(), egoh_decision)
    except (TypeError, ValidationError) as exc:
        return _result(
            chain_id=boundary["chain_id"],
            decision="held",
            reason="egoh-journal-held",
            evidence_decision=evidence_decision,
            lifecycle=lifecycle,
            egoh={"decision": egoh_decision, "journal": None},
            handoff=None,
        )
    handoff = build_handoff(egoh_decision, event, replayed=replayed)
    return _result(
        chain_id=boundary["chain_id"],
        decision="review-required",
        reason="synthetic-chain-complete",
        evidence_decision=evidence_decision,
        lifecycle=lifecycle,
        egoh={"decision": egoh_decision, "journal": {"event_sha256": event["event_sha256"], "replayed": replayed}},
        handoff=handoff,
    )


def run_boundary(boundary_value: object, *, clock: Callable[[], int] | None = None) -> dict[str, Any]:
    """Run one self-cleaning local synthetic chain with no output-path API."""
    with tempfile.TemporaryDirectory(prefix="operating-core-demo-") as directory:
        return _run_boundary_in_directory(boundary_value, Path(directory), clock=clock)
