"""Synthetic, local-only admission proof for one typed agent action.

The module commits a strict action request before running one fixed,
deterministic simulator.  It has no network, provider, subprocess, browser,
credential, filesystem-target, or real tool interface.  A successful result is
review-required metadata, never authority to execute an external effect.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping


REQUEST_SCHEMA = "synthetic-agent-action-request-v1"
REVIEW_SCHEMA = "synthetic-action-review-fixture-v1"
COMMITMENT_SCHEMA = "agent-action-pre-effect-commitment-v1"
RECEIPT_SCHEMA = "agent-action-simulation-receipt-v1"
OWNER_SNAPSHOT_SCHEMA = "agent-action-owner-snapshot-v1"
SIMULATOR_CONTRACT = "set-ticket-priority-deterministic-simulator-v1"
SIMULATOR_CONTRACT_SHA256 = hashlib.sha256(SIMULATOR_CONTRACT.encode("ascii")).hexdigest()
MAX_REVIEW_TTL_SECONDS = 3_600
MAX_OWNER_SNAPSHOT_BYTES = 262_144
MAX_OWNER_SNAPSHOT_COMMITMENTS = 64
TOOL_MANIFEST = {
    "name": "set-ticket-priority",
    "schema_version": "1",
    "argument_keys": ["priority", "ticket_id"],
    "allowed_priorities": ["high", "low", "normal"],
}
ACTION_ID = re.compile(r"[a-z0-9](?:[a-z0-9._-]{0,62}[a-z0-9])?")
TICKET_ID = re.compile(r"T-[1-9][0-9]{0,11}")


class AdmissionError(ValueError):
    """Stable reason code that never contains action payload bytes."""


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_json(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _reject_duplicate_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise AdmissionError("json-duplicate-key")
        result[key] = value
    return result


def _load_canonical_json(raw: object, reason: str) -> dict[str, Any]:
    return _load_canonical_json_bounded(raw, reason, 16_384)


def _load_canonical_json_bounded(
    raw: object,
    reason: str,
    maximum_bytes: int,
) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > maximum_bytes:
        raise AdmissionError(reason)
    try:
        decoded = raw.decode("utf-8")
        value = json.loads(decoded, object_pairs_hook=_reject_duplicate_pairs)
    except AdmissionError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AdmissionError(reason) from exc
    if type(value) is not dict or canonical_json(value).encode("utf-8") != raw:
        raise AdmissionError("json-noncanonical")
    return value


def _exact_dict(value: object, keys: set[str], reason: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        raise AdmissionError(reason)
    return value


def _parse_utc(value: object, reason: str) -> datetime:
    if type(value) is not str:
        raise AdmissionError(reason)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AdmissionError(reason) from exc
    if parsed.tzinfo is None:
        raise AdmissionError(reason)
    return parsed.astimezone(timezone.utc)


def _validate_request(raw: bytes) -> dict[str, Any]:
    request = _load_canonical_json(raw, "request-json-invalid")
    _exact_dict(request, {"schema", "action_id", "tool", "pre_state"}, "request-schema-invalid")
    if request["schema"] != REQUEST_SCHEMA or type(request["action_id"]) is not str or not ACTION_ID.fullmatch(request["action_id"]):
        raise AdmissionError("request-identity-invalid")
    tool = _exact_dict(request["tool"], {"name", "schema_version", "arguments"}, "tool-schema-invalid")
    if tool["name"] != TOOL_MANIFEST["name"]:
        raise AdmissionError("tool-unknown")
    if tool["schema_version"] != TOOL_MANIFEST["schema_version"]:
        raise AdmissionError("tool-version-invalid")
    arguments = _exact_dict(tool["arguments"], {"ticket_id", "priority"}, "tool-arguments-invalid")
    pre_state = _exact_dict(request["pre_state"], {"ticket_id", "priority"}, "pre-state-invalid")
    ticket_id = arguments["ticket_id"]
    if type(ticket_id) is not str or not TICKET_ID.fullmatch(ticket_id) or pre_state["ticket_id"] != ticket_id:
        raise AdmissionError("ticket-identity-invalid")
    if arguments["priority"] not in TOOL_MANIFEST["allowed_priorities"] or pre_state["priority"] not in TOOL_MANIFEST["allowed_priorities"]:
        raise AdmissionError("priority-invalid")
    if arguments["priority"] == pre_state["priority"]:
        raise AdmissionError("transition-noop")
    return request


def _expected_state(request: Mapping[str, Any]) -> dict[str, str]:
    return {
        "ticket_id": request["pre_state"]["ticket_id"],
        "priority": request["tool"]["arguments"]["priority"],
    }


@dataclass(frozen=True)
class Commitment:
    schema: str
    action_id: str
    request_sha256: str
    tool_manifest_sha256: str
    pre_state_sha256: str
    expected_state_sha256: str
    simulator_contract_sha256: str
    commitment_sha256: str
    _request_bytes: bytes
    _owner_nonce: object

    def public(self) -> dict[str, str]:
        return {
            "schema": self.schema,
            "action_id": self.action_id,
            "request_sha256": self.request_sha256,
            "tool_manifest_sha256": self.tool_manifest_sha256,
            "pre_state_sha256": self.pre_state_sha256,
            "expected_state_sha256": self.expected_state_sha256,
            "simulator_contract_sha256": self.simulator_contract_sha256,
            "commitment_sha256": self.commitment_sha256,
        }


class CommitmentOwner:
    """In-memory V1 owner; exact replay is accepted, identity conflict is held."""

    def __init__(self) -> None:
        self.__nonce = object()
        self._by_action_id: dict[str, Commitment] = {}

    def commit(self, raw_request: bytes) -> tuple[Commitment, bool]:
        request = _validate_request(raw_request)
        payload = {
            "schema": COMMITMENT_SCHEMA,
            "action_id": request["action_id"],
            "request_sha256": hashlib.sha256(raw_request).hexdigest(),
            "tool_manifest_sha256": sha256_json(TOOL_MANIFEST),
            "pre_state_sha256": sha256_json(request["pre_state"]),
            "expected_state_sha256": sha256_json(_expected_state(request)),
            "simulator_contract_sha256": SIMULATOR_CONTRACT_SHA256,
        }
        commitment = Commitment(
            **payload,
            commitment_sha256=sha256_json(payload),
            _request_bytes=bytes(raw_request),
            _owner_nonce=self.__nonce,
        )
        existing = self._by_action_id.get(commitment.action_id)
        if existing is not None:
            if existing.commitment_sha256 != commitment.commitment_sha256:
                raise AdmissionError("action-identity-conflict")
            return existing, True
        self._by_action_id[commitment.action_id] = commitment
        return commitment, False

    def require_current(self, commitment: object) -> Commitment:
        if type(commitment) is not Commitment:
            raise AdmissionError("commitment-owner-invalid")
        current = self._by_action_id.get(commitment.action_id)
        if current is not commitment or current._owner_nonce is not self.__nonce:
            raise AdmissionError("commitment-not-current")
        _assert_commitment_consistent(current)
        return current

    def export_snapshot(self) -> bytes:
        """Export one private caller-held continuity packet, never a receipt."""
        if len(self._by_action_id) > MAX_OWNER_SNAPSHOT_COMMITMENTS:
            raise AdmissionError("owner-snapshot-commitments-invalid")
        commitments = []
        for action_id in sorted(self._by_action_id):
            commitment = self.require_current(self._by_action_id[action_id])
            commitments.append({**commitment.public(), "request_hex": commitment._request_bytes.hex()})
        payload = {
            "schema": OWNER_SNAPSHOT_SCHEMA,
            "tool_manifest_sha256": sha256_json(TOOL_MANIFEST),
            "simulator_contract_sha256": SIMULATOR_CONTRACT_SHA256,
            "commitments": commitments,
        }
        snapshot = {**payload, "snapshot_sha256": sha256_json(payload)}
        encoded = canonical_json(snapshot).encode("utf-8")
        if len(encoded) > MAX_OWNER_SNAPSHOT_BYTES:
            raise AdmissionError("owner-snapshot-too-large")
        return encoded

    @classmethod
    def restore_snapshot(cls, raw_snapshot: bytes) -> "CommitmentOwner":
        """Rebuild process-local ownership from an exact caller-held packet."""
        snapshot = _load_canonical_json_bounded(
            raw_snapshot,
            "owner-snapshot-json-invalid",
            MAX_OWNER_SNAPSHOT_BYTES,
        )
        _exact_dict(
            snapshot,
            {
                "schema",
                "tool_manifest_sha256",
                "simulator_contract_sha256",
                "commitments",
                "snapshot_sha256",
            },
            "owner-snapshot-schema-invalid",
        )
        payload = {key: value for key, value in snapshot.items() if key != "snapshot_sha256"}
        if snapshot["schema"] != OWNER_SNAPSHOT_SCHEMA or snapshot["snapshot_sha256"] != sha256_json(payload):
            raise AdmissionError("owner-snapshot-binding-invalid")
        if snapshot["tool_manifest_sha256"] != sha256_json(TOOL_MANIFEST):
            raise AdmissionError("owner-snapshot-tool-manifest-drift")
        if snapshot["simulator_contract_sha256"] != SIMULATOR_CONTRACT_SHA256:
            raise AdmissionError("owner-snapshot-simulator-drift")
        entries = snapshot["commitments"]
        if type(entries) is not list or len(entries) > MAX_OWNER_SNAPSHOT_COMMITMENTS:
            raise AdmissionError("owner-snapshot-commitments-invalid")
        owner = cls()
        previous_action_id: str | None = None
        public_keys = {
            "schema",
            "action_id",
            "request_sha256",
            "tool_manifest_sha256",
            "pre_state_sha256",
            "expected_state_sha256",
            "simulator_contract_sha256",
            "commitment_sha256",
        }
        for entry_value in entries:
            entry = _exact_dict(
                entry_value,
                public_keys | {"request_hex"},
                "owner-snapshot-commitment-invalid",
            )
            action_id = entry["action_id"]
            if (
                type(action_id) is not str
                or not ACTION_ID.fullmatch(action_id)
                or previous_action_id is not None
                and action_id <= previous_action_id
            ):
                raise AdmissionError("owner-snapshot-order-invalid")
            request_hex = entry["request_hex"]
            if (
                type(request_hex) is not str
                or len(request_hex) > 32_768
                or len(request_hex) % 2
                or re.fullmatch(r"[0-9a-f]*", request_hex) is None
            ):
                raise AdmissionError("owner-snapshot-request-invalid")
            request_bytes = bytes.fromhex(request_hex)
            commitment = Commitment(
                **{key: entry[key] for key in public_keys},
                _request_bytes=request_bytes,
                _owner_nonce=owner.__nonce,
            )
            _assert_commitment_consistent(commitment)
            owner._by_action_id[action_id] = commitment
            previous_action_id = action_id
        return owner


def _assert_commitment_consistent(commitment: Commitment) -> None:
    """Re-derive every public binding from the immutable canonical request."""
    try:
        request = _validate_request(commitment._request_bytes)
    except AdmissionError as exc:
        raise AdmissionError("commitment-mutated") from exc
    payload = {
        "schema": COMMITMENT_SCHEMA,
        "action_id": request["action_id"],
        "request_sha256": hashlib.sha256(commitment._request_bytes).hexdigest(),
        "tool_manifest_sha256": sha256_json(TOOL_MANIFEST),
        "pre_state_sha256": sha256_json(request["pre_state"]),
        "expected_state_sha256": sha256_json(_expected_state(request)),
        "simulator_contract_sha256": SIMULATOR_CONTRACT_SHA256,
    }
    observed = {
        "schema": commitment.schema,
        "action_id": commitment.action_id,
        "request_sha256": commitment.request_sha256,
        "tool_manifest_sha256": commitment.tool_manifest_sha256,
        "pre_state_sha256": commitment.pre_state_sha256,
        "expected_state_sha256": commitment.expected_state_sha256,
        "simulator_contract_sha256": commitment.simulator_contract_sha256,
    }
    if observed != payload or commitment.commitment_sha256 != sha256_json(payload):
        raise AdmissionError("commitment-mutated")


def _validate_review(raw_review: bytes, commitment: Commitment, *, now: datetime) -> dict[str, Any]:
    review = _load_canonical_json(raw_review, "review-json-invalid")
    _exact_dict(
        review,
        {"schema", "action_id", "commitment_sha256", "decision", "reviewer_class", "observed_at", "expires_at", "claims"},
        "review-schema-invalid",
    )
    if review["schema"] != REVIEW_SCHEMA or review["decision"] != "approve-simulation-only":
        raise AdmissionError("review-decision-invalid")
    if review["reviewer_class"] != "synthetic-caller-attested-fixture":
        raise AdmissionError("reviewer-class-invalid")
    if review["action_id"] != commitment.action_id or review["commitment_sha256"] != commitment.commitment_sha256:
        raise AdmissionError("review-binding-invalid")
    observed_at = _parse_utc(review["observed_at"], "review-time-invalid")
    expires_at = _parse_utc(review["expires_at"], "review-time-invalid")
    current = now.astimezone(timezone.utc)
    if (
        observed_at > current
        or current > expires_at
        or expires_at <= observed_at
        or (expires_at - observed_at).total_seconds() > MAX_REVIEW_TTL_SECONDS
    ):
        raise AdmissionError("review-expired")
    claims = _exact_dict(review["claims"], {"human_authenticated", "provider_observed", "external_effect_authorized"}, "review-claims-invalid")
    if claims != {"human_authenticated": False, "provider_observed": False, "external_effect_authorized": False}:
        raise AdmissionError("review-authority-invalid")
    return review


def simulate_for_review(
    owner: CommitmentOwner,
    commitment: Commitment,
    raw_review: bytes,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Run only the fixed pure simulator and return raw-free review metadata."""
    if type(owner) is not CommitmentOwner:
        raise AdmissionError("commitment-owner-invalid")
    current = owner.require_current(commitment)
    reference = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    review = _validate_review(raw_review, current, now=reference)
    if current.simulator_contract_sha256 != SIMULATOR_CONTRACT_SHA256:
        raise AdmissionError("simulator-contract-drift")
    if current.tool_manifest_sha256 != sha256_json(TOOL_MANIFEST):
        raise AdmissionError("tool-manifest-drift")
    if hashlib.sha256(current._request_bytes).hexdigest() != current.request_sha256:
        raise AdmissionError("request-drift")
    request = _validate_request(current._request_bytes)
    next_state = _expected_state(request)
    if sha256_json(next_state) != current.expected_state_sha256:
        raise AdmissionError("simulated-transition-mismatch")
    receipt_payload = {
        "schema": RECEIPT_SCHEMA,
        "action_id": current.action_id,
        "commitment_sha256": current.commitment_sha256,
        "request_sha256": current.request_sha256,
        "tool_manifest_sha256": current.tool_manifest_sha256,
        "review_fixture_sha256": hashlib.sha256(raw_review).hexdigest(),
        "simulator_contract_sha256": SIMULATOR_CONTRACT_SHA256,
        "simulated_next_state_sha256": sha256_json(next_state),
        "status": "review-required",
        "authority": {
            "human_authenticated": False,
            "provider_observed": False,
            "network": False,
            "external_effect": False,
        },
        "effect_counters": {"tool_calls": 0, "network_calls": 0, "provider_mutations": 0, "external_writes": 0},
    }
    return {**receipt_payload, "receipt_sha256": sha256_json(receipt_payload)}


def run(raw_request: bytes, raw_review: bytes, *, now: datetime | None = None) -> dict[str, Any]:
    """Convenience path with a fresh owner; every invalid input is a named hold."""
    owner = CommitmentOwner()
    try:
        commitment, replayed = owner.commit(raw_request)
        receipt = simulate_for_review(owner, commitment, raw_review, now=now)
    except AdmissionError as exc:
        return {"status": "held", "reason": str(exc), "external_effect": False, "receipt": None}
    return {
        "status": "review-required",
        "reason": "synthetic-transition-recomputed",
        "commitment": commitment.public(),
        "commitment_replayed": replayed,
        "receipt": receipt,
        "external_effect": False,
    }
