#!/usr/bin/env python3
"""Deterministic evidence gate with no external action surface."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


TOP_LEVEL_KEYS = {
    "case_id",
    "required_facts",
    "min_independent_clusters",
    "risk_tags",
    "facts",
}
FACT_KEYS = {"name", "value", "source_id", "cluster", "captured_at", "expires_at"}
ALLOWED_RISK_TAGS = {
    "financial",
    "privacy",
    "safety",
    "legal",
    "account_mutation",
    "external_send",
}
IDENTIFIER = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._:-]{0,127}$")


class ContractError(ValueError):
    """Raised when input does not satisfy the public contract."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def content_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def parse_time(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ContractError(f"{field} must be a non-empty ISO-8601 string")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ContractError(f"{field} is not valid ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ContractError(f"{field} must include timezone")
    return parsed


def require_identifier(value: Any, field: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise ContractError(f"{field} has invalid identifier shape")
    return value


def require_scalar(value: Any, field: str) -> str | int | float | bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            raise ContractError(f"{field} must be finite")
        return value
    if isinstance(value, str) and 0 < len(value) <= 500:
        return value
    raise ContractError(f"{field} must be a bounded scalar")


@dataclass(frozen=True)
class Fact:
    name: str
    value: str | int | float | bool
    source_id: str
    cluster: str
    captured_at: datetime
    expires_at: datetime

    @classmethod
    def decode(cls, raw: Any, index: int) -> "Fact":
        if not isinstance(raw, dict) or set(raw) != FACT_KEYS:
            raise ContractError(f"facts[{index}] must contain exactly {sorted(FACT_KEYS)}")
        captured = parse_time(raw["captured_at"], f"facts[{index}].captured_at")
        expires = parse_time(raw["expires_at"], f"facts[{index}].expires_at")
        if expires <= captured:
            raise ContractError(f"facts[{index}] must expire after capture")
        return cls(
            name=require_identifier(raw["name"], f"facts[{index}].name"),
            value=require_scalar(raw["value"], f"facts[{index}].value"),
            source_id=require_identifier(raw["source_id"], f"facts[{index}].source_id"),
            cluster=require_identifier(raw["cluster"], f"facts[{index}].cluster"),
            captured_at=captured,
            expires_at=expires,
        )

    def trace(self) -> dict[str, Any]:
        raw = {
            "name": self.name,
            "value": self.value,
            "source_id": self.source_id,
            "cluster": self.cluster,
            "captured_at": self.captured_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
        }
        return {**raw, "fact_hash": content_hash(raw)}


@dataclass(frozen=True)
class WorkflowCase:
    case_id: str
    required_facts: tuple[str, ...]
    min_independent_clusters: int
    risk_tags: tuple[str, ...]
    facts: tuple[Fact, ...]
    raw_hash: str

    @classmethod
    def decode(cls, raw: Any) -> "WorkflowCase":
        if not isinstance(raw, dict) or set(raw) != TOP_LEVEL_KEYS:
            raise ContractError(f"input must contain exactly {sorted(TOP_LEVEL_KEYS)}")
        case_id = require_identifier(raw["case_id"], "case_id")
        required_raw = raw["required_facts"]
        if not isinstance(required_raw, list) or not 1 <= len(required_raw) <= 50:
            raise ContractError("required_facts must contain 1..50 identifiers")
        required = tuple(require_identifier(item, "required_facts[]") for item in required_raw)
        if len(set(required)) != len(required):
            raise ContractError("required_facts must be unique")
        minimum = raw["min_independent_clusters"]
        if not isinstance(minimum, int) or isinstance(minimum, bool) or not 1 <= minimum <= 3:
            raise ContractError("min_independent_clusters must be an integer in 1..3")
        risks_raw = raw["risk_tags"]
        if not isinstance(risks_raw, list) or len(risks_raw) > len(ALLOWED_RISK_TAGS):
            raise ContractError("risk_tags must be a bounded list")
        risks = tuple(sorted(set(risks_raw)))
        if len(risks) != len(risks_raw) or not set(risks) <= ALLOWED_RISK_TAGS:
            raise ContractError("risk_tags contain duplicate or unsupported values")
        facts_raw = raw["facts"]
        if not isinstance(facts_raw, list) or len(facts_raw) > 100:
            raise ContractError("facts must be a list with at most 100 rows")
        facts = tuple(Fact.decode(item, index) for index, item in enumerate(facts_raw))
        return cls(case_id, required, minimum, risks, facts, content_hash(raw))


def evaluate(raw: Any, as_of_text: str) -> dict[str, Any]:
    case = WorkflowCase.decode(raw)
    as_of = parse_time(as_of_text, "as_of")
    findings: list[dict[str, Any]] = []
    used: list[Fact] = []

    for required_name in case.required_facts:
        candidates = [fact for fact in case.facts if fact.name == required_name]
        if not candidates:
            findings.append({"fact": required_name, "kind": "missing"})
            continue
        fresh = [fact for fact in candidates if fact.captured_at <= as_of < fact.expires_at]
        if not fresh:
            findings.append({"fact": required_name, "kind": "stale"})
            continue
        values = {canonical_json(fact.value) for fact in fresh}
        if len(values) != 1:
            findings.append(
                {"fact": required_name, "kind": "conflict", "value_count": len(values)}
            )
            continue
        clusters = {fact.cluster for fact in fresh}
        if len(clusters) < case.min_independent_clusters:
            findings.append(
                {
                    "fact": required_name,
                    "kind": "insufficient_independence",
                    "observed_clusters": len(clusters),
                    "required_clusters": case.min_independent_clusters,
                }
            )
            continue
        used.extend(sorted(fresh, key=lambda item: (item.cluster, item.source_id)))

    if findings:
        decision, reason = "hold", "EVIDENCE_NOT_ADMISSIBLE"
    elif case.risk_tags:
        decision, reason = "escalate", "HUMAN_AUTHORITY_REQUIRED"
    else:
        decision, reason = "draft", "EVIDENCE_COMPLETE"

    return {
        "schema": "evidence-gated-workflow-decision-v1",
        "case_id": case.case_id,
        "decision": decision,
        "reason": reason,
        "as_of": as_of.isoformat(),
        "input_sha256": case.raw_hash,
        "risk_tags": list(case.risk_tags),
        "findings": findings,
        "evidence": [fact.trace() for fact in used],
        "external_action_authorized": False,
        "model_call_performed": False,
        "network_access_performed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--as-of", required=True)
    args = parser.parse_args()
    raw = json.loads(args.input.read_text(encoding="utf-8"))
    print(json.dumps(evaluate(raw, args.as_of), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
