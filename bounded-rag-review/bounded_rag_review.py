"""Deterministic local source retrieval with a review-only terminal boundary.

This is not an LLM or semantic RAG implementation. It binds synthetic source
text to SHA-256, ranks exact lexical overlap, and emits raw-free review metadata.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Iterable

REQUEST_SCHEMA = "bounded-local-context-review-request-v1"
RESULT_SCHEMA = "bounded-local-context-review-result-v1"
TOKEN_RE = re.compile(r"[a-z0-9_]+")
SOURCE_ID_RE = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")
DIGEST_RE = re.compile(r"[0-9a-f]{64}")
NON_SIGNAL_TOKENS = frozenset({"a", "an", "and", "are", "do", "for", "how", "i", "in", "is", "of", "the", "to", "what"})
class ReviewHold(ValueError):
    """The local request or source family cannot be admitted."""


@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    text: str
    sha256: str


def canonical_json(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")


def _utf8(value: str, reason: str) -> bytes:
    try:
        return value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ReviewHold(reason) from exc


def _false_authority() -> dict[str, bool]:
    return {
        "external_action": False, "human_review_authenticated": False,
        "llm_called": False, "network": False, "production": False,
        "provider_observed": False, "semantic_quality_proven": False,
    }


def source_record(source_id: str, text: str) -> SourceRecord:
    if type(source_id) is not str or SOURCE_ID_RE.fullmatch(source_id) is None:
        raise ReviewHold("source-id-invalid")
    if type(text) is not str or not text.strip():
        raise ReviewHold("source-text-invalid")
    encoded = _utf8(text, "source-text-invalid")
    if len(encoded) > 65_536:
        raise ReviewHold("source-text-invalid")
    return SourceRecord(source_id, text, hashlib.sha256(encoded).hexdigest())


def _tokens(text: str) -> frozenset[str]:
    return frozenset(TOKEN_RE.findall(text.lower())) - NON_SIGNAL_TOKENS


def _strict_object(raw: bytes) -> dict[str, object]:
    if not isinstance(raw, bytes) or not raw or len(raw) > 16_384:
        raise ReviewHold("request-bytes-invalid")

    def pairs(items: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in items:
            if key in result:
                raise ReviewHold("request-duplicate-key")
            result[key] = value
        return result

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReviewHold("request-json-invalid") from exc
    if not isinstance(value, dict):
        raise ReviewHold("request-object-required")
    if raw != canonical_json(value):
        raise ReviewHold("request-canonical-json-required")
    return value


def _validated_records(records: Iterable[SourceRecord]) -> tuple[SourceRecord, ...]:
    family = tuple(records)
    if not family or len(family) > 256:
        raise ReviewHold("source-family-empty")
    ids: set[str] = set()
    hashes: set[str] = set()
    canonical: list[SourceRecord] = []
    for record in family:
        if type(record) is not SourceRecord:
            raise ReviewHold("source-record-invalid")
        source_id, text, declared_digest = record.source_id, record.text, record.sha256
        if type(source_id) is not str or SOURCE_ID_RE.fullmatch(source_id) is None:
            raise ReviewHold("source-id-invalid")
        if type(text) is not str or not text.strip():
            raise ReviewHold("source-text-invalid")
        if type(declared_digest) is not str or DIGEST_RE.fullmatch(declared_digest) is None:
            raise ReviewHold("source-digest-invalid")
        encoded = _utf8(text, "source-text-invalid")
        if len(encoded) > 65_536:
            raise ReviewHold("source-text-invalid")
        if source_id in ids:
            raise ReviewHold("source-id-duplicate")
        current = hashlib.sha256(encoded).hexdigest()
        if current != declared_digest:
            raise ReviewHold("source-digest-conflict")
        if current in hashes:
            raise ReviewHold("source-content-duplicate")
        ids.add(source_id)
        hashes.add(current)
        canonical.append(SourceRecord(source_id, text, current))
    return tuple(canonical)


def review(raw_request: bytes, records: Iterable[SourceRecord]) -> dict[str, object]:
    request = _strict_object(raw_request)
    if set(request) != {"query", "requested_effect", "schema"}:
        raise ReviewHold("request-fields-invalid")
    if request["schema"] != REQUEST_SCHEMA:
        raise ReviewHold("request-schema-invalid")
    query = request["query"]
    effect = request["requested_effect"]
    if not isinstance(query, str) or not query.strip():
        raise ReviewHold("query-invalid")
    query_bytes = _utf8(query, "query-invalid")
    if len(query_bytes) > 2048:
        raise ReviewHold("query-invalid")
    if not isinstance(effect, str):
        raise ReviewHold("requested-effect-invalid")

    family = _validated_records(records)
    query_tokens = _tokens(query)
    ranked = sorted(
        ((len(query_tokens & _tokens(item.text)), item.source_id, item.sha256) for item in family),
        key=lambda item: (-item[0], item[1], item[2]),
    )
    matches = [
        {"overlap_count": overlap, "source_id": source_id, "source_sha256": digest}
        for overlap, source_id, digest in ranked if overlap > 0
    ][:2]
    if effect != "review_only":
        decision, reason, matches = "held-effect-boundary", "requested-effect-requires-separate-authority", []
    elif not matches:
        decision, reason = "held-no-lexical-context", "no-exact-lexical-overlap"
    else:
        decision, reason = "local-context-review-ready", "source-bound-local-context-available"

    result: dict[str, object] = {
        "authority": _false_authority(), "decision": decision, "matches": matches,
        "query_sha256": hashlib.sha256(query_bytes).hexdigest(),
        "reason": reason, "request_sha256": hashlib.sha256(raw_request).hexdigest(),
        "schema": RESULT_SCHEMA,
        "source_family_sha256": hashlib.sha256(canonical_json([
            {"source_id": item.source_id, "source_sha256": item.sha256}
            for item in sorted(family, key=lambda item: item.source_id)
        ])).hexdigest(),
    }
    result["result_sha256"] = hashlib.sha256(canonical_json(result)).hexdigest()
    return result


def demo_records() -> tuple[SourceRecord, ...]:
    return (
        source_record("workflow-contract", "A reliable workflow has typed input, explicit owner, bounded retry, an idempotency key and a reviewable handoff."),
        source_record("effect-boundary", "Production mutations, credentials and customer data require separate authority."),
        source_record("acceptance", "Acceptance names one measurable result, known failures and a human approval boundary."),
    )
