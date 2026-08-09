"""Local, synthetic Evidence-Gated Operator Handoff demo.

This module deliberately has no network, browser, provider, subprocess, or
credential interface. Its only persistent surface is an owner-bound local JSONL
journal. A decision never performs an external effect.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCENARIO_SCHEMA = "egoh-synthetic-scenario-v1"
EVIDENCE_SCHEMA = "egoh-synthetic-evidence-v1"
JOURNAL_SCHEMA = "egoh-decision-journal-v1"
HANDOFF_SCHEMA = "egoh-operator-handoff-v1"
ALLOWED_TOOLS = frozenset(
    {"observe-structure", "verify-digest", "record-decision", "build-handoff"}
)
FORBIDDEN_HANDOFF_KEYS = frozenset(
    {
        "api_key", "authorization", "cookie", "credential", "email", "page_text",
        "password", "raw_url", "recipient", "secret", "session", "session_id", "token",
    }
)
MAX_TTL_SECONDS = 86_400


class ValidationError(ValueError):
    """A stable safe reason code; never include fixture content in the message."""


class OwnedJournal:
    """A journal path minted by an owner-checked root; raw paths are not accepted."""

    def __init__(self, root: Path, path: Path) -> None:
        self._root = root
        self._path = path

    @property
    def path(self) -> Path:
        """Local inspection path; write APIs still require this owned object."""
        return self._path

    def assert_valid(self) -> None:
        _assert_owned_directory(self._root)
        _assert_no_symlink_path(self._root, self._path)
        if self._path.exists():
            mode = os.lstat(self._path).st_mode
            if not stat.S_ISREG(mode):
                raise ValidationError("journal-path-not-regular")


class JournalOwner:
    """Mints journal targets only beneath one existing, caller-owned directory."""

    def __init__(self, output_root: Path) -> None:
        if not isinstance(output_root, Path):
            raise TypeError("output_root must be Path")
        self._root = output_root.absolute()
        _assert_owned_directory(self._root)

    def journal(self, relative: str = "journal.jsonl") -> OwnedJournal:
        if not isinstance(relative, str):
            raise TypeError("journal relative path must be str")
        requested = Path(relative)
        if requested.is_absolute() or not requested.parts or any(part in {"", ".", ".."} for part in requested.parts):
            raise ValidationError("journal-relative-invalid")
        candidate = self._root.joinpath(*requested.parts)
        _assert_no_symlink_path(self._root, candidate)
        parent = candidate.parent
        if not parent.is_dir():
            raise ValidationError("journal-parent-missing")
        if candidate.exists() and not stat.S_ISREG(os.lstat(candidate).st_mode):
            raise ValidationError("journal-path-not-regular")
        return OwnedJournal(self._root, candidate)


def _assert_owned_directory(path: Path) -> None:
    try:
        metadata = os.lstat(path)
    except OSError as exc:
        raise ValidationError("journal-root-unreadable") from exc
    if stat.S_ISLNK(metadata.st_mode):
        raise ValidationError("journal-root-symlink")
    if not stat.S_ISDIR(metadata.st_mode):
        raise ValidationError("journal-root-not-directory")
    if metadata.st_uid != os.geteuid():
        raise ValidationError("journal-root-not-owned")


def _assert_no_symlink_path(root: Path, candidate: Path) -> None:
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise ValidationError("journal-outside-owner-root") from exc
    current = root
    for part in relative.parts:
        current = current / part
        try:
            metadata = os.lstat(current)
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise ValidationError("journal-path-unreadable") from exc
        if stat.S_ISLNK(metadata.st_mode):
            raise ValidationError("journal-path-symlink")


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_json(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def parse_utc(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValidationError("timestamp-invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError("timestamp-invalid") from exc
    if parsed.tzinfo is None:
        raise ValidationError("timestamp-timezone-required")
    return parsed.astimezone(timezone.utc)


def _exact_keys(value: object, keys: set[str], code: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValidationError(code)
    return value


def _bounded_int(value: object, maximum: int, code: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= maximum:
        raise ValidationError(code)
    return value


def validate_evidence(value: object) -> dict[str, Any]:
    evidence = _exact_keys(
        value,
        {"schema", "scenario_id", "observed_at", "freshness_ttl_seconds", "projection", "claims"},
        "evidence-schema-invalid",
    )
    if evidence["schema"] != EVIDENCE_SCHEMA:
        raise ValidationError("evidence-schema-unsupported")
    if not isinstance(evidence["scenario_id"], str) or not evidence["scenario_id"]:
        raise ValidationError("evidence-scenario-invalid")
    parse_utc(evidence["observed_at"])
    _bounded_int(evidence["freshness_ttl_seconds"], MAX_TTL_SECONDS, "evidence-ttl-invalid")
    if evidence["freshness_ttl_seconds"] == 0:
        raise ValidationError("evidence-ttl-invalid")
    projection = _exact_keys(
        evidence["projection"],
        {"form_count", "field_count", "application_form_candidate_present"},
        "evidence-projection-invalid",
    )
    form_count = _bounded_int(projection["form_count"], 1000, "evidence-projection-invalid")
    field_count = _bounded_int(projection["field_count"], 10_000, "evidence-projection-invalid")
    if not isinstance(projection["application_form_candidate_present"], bool):
        raise ValidationError("evidence-projection-invalid")
    if form_count == 0 and field_count != 0:
        raise ValidationError("evidence-projection-invalid")
    claims = _exact_keys(
        evidence["claims"],
        {"external_action", "page_content_output", "provider_delivery_observed", "application_submitted"},
        "evidence-claims-invalid",
    )
    if claims != {
        "external_action": False,
        "page_content_output": False,
        "provider_delivery_observed": False,
        "application_submitted": False,
    }:
        raise ValidationError("evidence-boundary-invalid")
    return evidence


def validate_scenario(value: object) -> dict[str, Any]:
    scenario = _exact_keys(
        value,
        {"schema", "scenario_id", "tool_intent", "evidence", "evidence_sha256"},
        "scenario-schema-invalid",
    )
    if scenario["schema"] != SCENARIO_SCHEMA:
        raise ValidationError("scenario-schema-unsupported")
    if not isinstance(scenario["scenario_id"], str) or not scenario["scenario_id"]:
        raise ValidationError("scenario-id-invalid")
    if not isinstance(scenario["tool_intent"], str) or not scenario["tool_intent"]:
        raise ValidationError("tool-intent-invalid")
    if not isinstance(scenario["evidence_sha256"], str) or len(scenario["evidence_sha256"]) != 64:
        raise ValidationError("evidence-digest-invalid")
    if any(char not in "0123456789abcdef" for char in scenario["evidence_sha256"]):
        raise ValidationError("evidence-digest-invalid")
    evidence = validate_evidence(scenario["evidence"])
    if evidence["scenario_id"] != scenario["scenario_id"]:
        raise ValidationError("evidence-scenario-mismatch")
    return scenario


def _safe_held(reason: str, scenario_id: str = "unknown") -> dict[str, Any]:
    return {
        "scenario_id": scenario_id,
        "decision": "held",
        "reason": reason,
        "evidence_sha256": None,
        "external_action": False,
        "effect_counters": zero_effect_counters(),
    }


def zero_effect_counters() -> dict[str, int]:
    return {
        "network_calls": 0,
        "browser_writes": 0,
        "provider_mutations": 0,
        "submissions": 0,
        "payments": 0,
    }


def validate_readonly_observation_target(
    *, cdp_list_url: object, websocket_url: object, matching_tab_count: object, frame_bytes: object
) -> None:
    """Validate a synthetic CDP-like target without opening a socket or browser.

    The helper exists solely to prove the admission boundary in fixtures/tests.
    It does not fetch URLs, inspect a page, or retain any URL in its result.
    """
    if cdp_list_url != "http://127.0.0.1:9222/json/list":
        raise ValidationError("cdp-loopback-invalid")
    if not isinstance(websocket_url, str) or not websocket_url.startswith("ws://127.0.0.1:9222/devtools/page/"):
        raise ValidationError("cdp-loopback-invalid")
    if _bounded_int(matching_tab_count, 1, "target-ambiguous") != 1:
        raise ValidationError("target-ambiguous")
    if _bounded_int(frame_bytes, 65_536, "cdp-frame-invalid") == 0:
        raise ValidationError("cdp-frame-invalid")


def assert_redacted_handoff(value: object) -> None:
    """Reject known sensitive field names anywhere in a handoff tree."""
    if isinstance(value, dict):
        for key, child in value.items():
            normalized_key = key.strip().lower().replace("-", "_")
            if normalized_key in FORBIDDEN_HANDOFF_KEYS:
                raise ValidationError("handoff-forbidden-field")
            assert_redacted_handoff(child)
    elif isinstance(value, list):
        for child in value:
            assert_redacted_handoff(child)


def decide(scenario_value: object, *, now: datetime | None = None) -> dict[str, Any]:
    """Return a fail-closed local decision. Invalid input remains non-effecting."""
    scenario_id = scenario_value.get("scenario_id", "unknown") if isinstance(scenario_value, dict) else "unknown"
    try:
        scenario = validate_scenario(scenario_value)
    except ValidationError as exc:
        return _safe_held(str(exc), scenario_id if isinstance(scenario_id, str) else "unknown")
    if scenario["tool_intent"] not in ALLOWED_TOOLS:
        return _safe_held("tool-denied", scenario["scenario_id"])
    actual_digest = sha256_json(scenario["evidence"])
    if actual_digest != scenario["evidence_sha256"]:
        return _safe_held("evidence-digest-mismatch", scenario["scenario_id"])
    observed_at = parse_utc(scenario["evidence"]["observed_at"])
    reference = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    age_seconds = (reference - observed_at).total_seconds()
    if age_seconds < 0 or age_seconds > scenario["evidence"]["freshness_ttl_seconds"]:
        return _safe_held("evidence-stale", scenario["scenario_id"])
    if not scenario["evidence"]["projection"]["application_form_candidate_present"]:
        return _safe_held("application-form-not-observed", scenario["scenario_id"])
    return {
        "scenario_id": scenario["scenario_id"],
        "decision": "review-required",
        "reason": "synthetic-evidence-accepted",
        "evidence_sha256": actual_digest,
        "external_action": False,
        "effect_counters": zero_effect_counters(),
    }


def _event_payload(decision: dict[str, Any], predecessor_event_sha256: str | None) -> dict[str, Any]:
    return {
        "schema": JOURNAL_SCHEMA,
        "scenario_id": decision["scenario_id"],
        "decision": decision["decision"],
        "reason": decision["reason"],
        "evidence_sha256": decision["evidence_sha256"],
        "external_action": False,
        "effect_counters": zero_effect_counters(),
        "predecessor_event_sha256": predecessor_event_sha256,
    }


def _require_owned_journal(value: object) -> OwnedJournal:
    if not isinstance(value, OwnedJournal):
        raise TypeError("journal must be OwnedJournal")
    value.assert_valid()
    return value


def read_journal(journal: OwnedJournal) -> list[dict[str, Any]]:
    path = _require_owned_journal(journal).path
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValidationError("journal-unreadable") from exc
    predecessor: str | None = None
    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValidationError("journal-json-invalid") from exc
        expected_keys = {
            "schema", "scenario_id", "decision", "reason", "evidence_sha256", "external_action",
            "effect_counters", "predecessor_event_sha256", "event_sha256",
        }
        if not isinstance(event, dict) or set(event) != expected_keys:
            raise ValidationError("journal-schema-invalid")
        payload = {key: event[key] for key in event if key != "event_sha256"}
        if event["schema"] != JOURNAL_SCHEMA or event["predecessor_event_sha256"] != predecessor:
            raise ValidationError("journal-chain-invalid")
        if event["event_sha256"] != sha256_json(payload):
            raise ValidationError("journal-digest-invalid")
        if event["external_action"] is not False or event["effect_counters"] != zero_effect_counters():
            raise ValidationError("journal-effect-boundary-invalid")
        predecessor = event["event_sha256"]
        rows.append(event)
    return rows


def record_decision(journal: OwnedJournal, decision: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Append one valid decision or return the exact prior event for a replay."""
    journal = _require_owned_journal(journal)
    existing = read_journal(journal)
    replay_key = (decision["scenario_id"], decision["evidence_sha256"], decision["decision"])
    for event in existing:
        event_key = (event["scenario_id"], event["evidence_sha256"], event["decision"])
        if event_key == replay_key:
            return event, True
        if event["scenario_id"] == decision["scenario_id"] and event["evidence_sha256"] != decision["evidence_sha256"]:
            raise ValidationError("journal-scenario-conflict")
    predecessor = existing[-1]["event_sha256"] if existing else None
    event = _event_payload(decision, predecessor)
    event["event_sha256"] = sha256_json(event)
    flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(journal.path, flags, 0o600)
    except OSError as exc:
        raise ValidationError("journal-append-failed") from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.geteuid():
            raise ValidationError("journal-path-not-regular")
        with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
            descriptor = -1
            handle.write(canonical_json(event) + "\n")
    finally:
        if descriptor != -1:
            os.close(descriptor)
    return event, False


def build_handoff(decision: dict[str, Any], event: dict[str, Any], *, replayed: bool) -> dict[str, Any] | None:
    if decision["decision"] != "review-required":
        return None
    handoff = {
        "schema": HANDOFF_SCHEMA,
        "scenario_id": decision["scenario_id"],
        "evidence_sha256": decision["evidence_sha256"],
        "decision": decision["decision"],
        "journal_event_sha256": event["event_sha256"],
        "known": ["synthetic evidence schema validated", "digest bound", "no external action"],
        "unknown": ["provider state", "delivery", "contract", "income"],
        "required_human_action": "Review the local handoff; any external action needs separate named authority and provider-side readback.",
        "boundary": {
            "external_action": False,
            "approval_recorded": False,
            "provider_delivery_observed": False,
            "application_submitted": False,
        },
        "replayed": replayed,
    }
    assert_redacted_handoff(handoff)
    return handoff


def run_scenario(path: Path, journal: OwnedJournal, *, now: datetime | None = None) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raw = {"scenario_id": "unknown"}
        decision = _safe_held("fixture-invalid")
    else:
        decision = decide(raw, now=now)
    result: dict[str, Any] = {"decision": decision, "journal": None, "handoff": None}
    try:
        event, replayed = record_decision(journal, decision)
    except ValidationError as exc:
        result["decision"] = _safe_held(str(exc), str(decision["scenario_id"]))
        return result
    result["journal"] = {"event_sha256": event["event_sha256"], "replayed": replayed}
    result["handoff"] = build_handoff(decision, event, replayed=replayed)
    return result
