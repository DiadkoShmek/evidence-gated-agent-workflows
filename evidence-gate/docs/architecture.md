# Architecture

## Entrypoint

`python3 -m src.evidence_gate --input FILE --as-of TIMESTAMP`

## Flow

1. Strict decoder rejects unknown top-level or fact fields.
2. Identifiers, bounded scalar values, timezone-aware timestamps, and size caps are validated.
3. Each required fact is checked for presence, freshness, value consistency, and source-cluster independence.
4. Evidence failure produces `hold`.
5. Complete evidence plus a bounded risk tag produces `escalate`.
6. Complete non-risk evidence produces internal `draft`.
7. Every result carries normalized input and fact hashes plus explicit zero-action counters.

## Main contracts

- Input must use one exact schema; unknown instruction-shaped fields fail closed.
- Evidence is admissible only at the caller-supplied, timezone-aware `as_of` boundary.
- Multiple fresh values for one required fact are a conflict, not a majority vote.
- Independence is measured by declared source clusters, not raw URL/source count.
- No decision authorizes an external action.

## Failure modes

- malformed or widened input → `ContractError`;
- missing/stale/conflicting/under-independent fact → `hold` trace;
- high-risk complete case → `escalate`;
- stress drift or time overflow → non-zero exit.

## Stability

The core is pure standard-library Python, has no network/model dependency, uses canonical JSON for hashes, and has a finite stress harness. It is intentionally small enough to audit.
