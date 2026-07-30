# Evidence-gated Workflow Demo

A small, deterministic reference implementation for AI-assisted workflows that
must not invent missing facts or take external action.

It turns structured evidence into one of three internal states:

- `draft` — required evidence is fresh, consistent, and sufficiently independent;
- `escalate` — evidence is complete, but the case needs human authority;
- `hold` — evidence is missing, stale, conflicting, or insufficiently independent.

The demo does **not** call a model, use the network, send a message, or mutate an
external system.

## Run

```bash
python3 -m src.evidence_gate \
  --input fixtures/clean.json \
  --as-of 2026-07-30T12:00:00Z
```

## Test

```bash
python3 -m unittest -v tests/test_evidence_gate.py
```

## Stress

```bash
python3 scripts/stress.py --iterations 1000
```

The stress command repeats all five fixture families and fails on output drift,
unexpected decisions, exceptions, or time-budget overflow.

## Example

Excerpt from the clean input (the runnable fixture also contains `policy_limit`):

```json
{
  "case_id": "clean-case",
  "required_facts": ["account_status", "policy_limit"],
  "min_independent_clusters": 1,
  "risk_tags": [],
  "facts": [
    {
      "name": "account_status",
      "value": "active",
      "source_id": "account-record-1",
      "cluster": "system-of-record",
      "captured_at": "2026-07-30T10:00:00Z",
      "expires_at": "2026-07-31T10:00:00Z"
    }
  ]
}
```

Output includes the decision, reason, findings, evidence trace, normalized input
hash, and explicit `external_action_authorized=false`.

## Architecture

`JSON input → strict decoder → evidence checks → risk boundary → decision trace`

See [architecture](docs/architecture.md) and [limits](docs/limits.md).
The latest local receipt is recorded in [proof](docs/proof.md).

## Verified

- strict top-level and fact schemas;
- timezone-aware timestamps;
- missing, stale, conflict, and independence holds;
- an explicit human-escalation state for bounded risk tags;
- deterministic output and stable content hashes;
- finite local stress run;
- no model, network, transport, credential, or external-effect surface.
