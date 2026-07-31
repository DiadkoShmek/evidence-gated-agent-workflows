# Integration Reliability Acceptance Pack

Use this pack for one paid discovery and control-plane slice around an existing
client workflow. The goal is to make one source-to-target path reviewable before
any production activation.

## Buyer inputs

- one named workflow and decision owner;
- current platform and version;
- one client-owned test environment;
- sanitized request, response, and failure examples;
- the action that must remain human-approved;
- one measurable acceptance result.

No credential, customer record, payment action, publishing route, or production
endpoint is needed for the discovery phase.

## Deliverables

1. **Interface contract** — typed inputs and outputs, authentication boundary,
   source and target ownership, and versioned endpoint assumptions.
2. **Job lifecycle** — request fingerprint, persisted external job ID, polling
   deadline, bounded retry policy, and explicit terminal states.
3. **Decision table** — the exact evidence required for `complete`, `review`,
   `failed`, and `timed-out`; missing or malformed evidence never becomes
   success.
4. **Approval boundary** — actions that require a named human decision and the
   receipt expected after that decision.
5. **Test and handoff pack** — sanitized fixtures, hostile-path test matrix,
   run receipt schema, known limits, and an implementation runbook.

## Acceptance tests

- the same request fingerprint cannot create a second submission;
- the external job ID is persisted before the first poll;
- only an explicit completed state plus required output metadata becomes
  `complete`;
- timeout, crash, malformed response, unknown ID, and missing output become
  reviewable terminal states;
- every run receipt records the declared platform version, endpoint contract,
  fixture hashes, decision, and test result;
- no external send, publishing action, payment, or account mutation occurs
  without separate authority and a provider-side readback.

## Evidence already available

A dependency-free Python reference demonstrates the underlying control-plane
patterns: fingerprint idempotency, bounded backoff, hard timeout, explicit
failure states, and honest handling of unknown IDs. It intentionally uses a fake
worker and does not claim n8n, Make, ComfyUI, GPU, multi-writer, or production
deployment compatibility.

Public reference:
https://github.com/DiadkoShmek/evidence-gated-agent-workflows/tree/f60c8a811088a72ca69fe17e5e1c5d3165303ad4

## Commercial boundary

The first slice is discovery plus a reviewable control contract, hostile test
matrix, and handoff runbook. A platform-specific draft workflow is included only
after the buyer supplies the exact platform version, endpoint schema, and a test
environment. Production activation, real credentials, multi-workflow rollout,
performance guarantees, and claims of prior platform deployment are excluded.
