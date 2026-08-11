# Evidence-gated Agent Workflows

Two small, dependency-free Python references for automation systems that must
fail honestly instead of inventing a successful result.

## For AI engineers

Read the [architecture of the evidence-gated boundary](https://diadkoshmek.github.io/evidence-gated-agent-workflows/architecture.html)
before the service page. It separates four checked owners instead of presenting
one vague “AI safety” layer:

- exact evidence admission with fact identity, hashes, freshness and conflicts;
- fingerprint reuse and bounded terminal states for asynchronous polling;
- scenario/evidence/decision replay and conflict refusal in the EGOH journal;
- a composed synthetic core that requires lifecycle completion and independent
  EGOH acceptance before producing a review-required handoff.

The public reference keeps external action authority false. Descriptor-bound
source/target revalidation is implemented only when a real adapter contract
requires it; it is not claimed by the synthetic demo.

For teams working on agent memory, retrieval, evaluation, tool execution, or
durable workflow state, the [AI Systems Proof Sprint](https://diadkoshmek.github.io/evidence-gated-agent-workflows/ai-systems-sprint.html)
maps four purchasable code seams to exact evidence, refusal paths, deliverables,
and acceptance criteria.

## Work with me

I offer a fixed-scope **AI Systems Proof Sprint**: one fail-closed provenance
adapter for one sanitized AI or data handoff. You bring its expected schema,
the source and target interface descriptions, and one costly failure the
handoff must refuse. In 3–5 working days I build a bounded adapter, hostile
test suite, decision trace, known-limits report, and engineering handoff. The
fixed first-step price is **$1,500**.

[View the AI Systems Proof Sprint](https://diadkoshmek.github.io/evidence-gated-agent-workflows/ai-systems-sprint.html)
or [inspect the architecture](https://diadkoshmek.github.io/evidence-gated-agent-workflows/architecture.html)
or [open a scoped public workflow inquiry](https://github.com/DiadkoShmek/evidence-gated-agent-workflows/issues/new?template=client-inquiry.yml).
Do not put credentials, personal/customer data, private code, or production
access details in a public issue.

For clients: this demonstrates how I make AI workflows observable and honest
about failure before they are connected to real systems.

The pilot is accepted when the agreed valid fixture passes, the agreed hostile
fixtures fail closed with named reasons, and the documented proof command is
green. One review round is included. Production deployment, security or
compliance certification, SLA, ongoing support, client-system access, and
automatic activation are outside this pilot. Repository and licensing terms
are agreed before work begins. The public demo tests demonstrate only the
checked-in demo; they are not a safety guarantee for a client adapter.

## A staged system, with one purchasable first step

The fixed AI Systems Proof Sprint is deliberately the only item for sale now: **one fail-closed handoff**
with a bounded acceptance proof. It is the evidence needed to decide whether any larger
system work is justified.

1. **Now — fixed purchasable sprint.** The AI Systems Proof Sprint above
   produces one bounded fail-closed provenance adapter, hostile proof, decision trace,
   known-limits report, and handoff.
2. **After Stage 1 evidence — separately scoped hardening.** If that proof
   reveals a real boundary worth carrying forward, a later written scope can
   harden an agent/runtime control plane around that boundary. It is not
   included, priced, or promised by the first sprint.
3. **After evidence — operator system roadmap.** A later roadmap can name the
   next operator decisions, proof gaps, and ownership boundaries. It does not
   authorize implementation or imply that a later layer will be needed.

This is a progression of evidence, not a bundled platform offer: the first
handoff must earn every later conversation.

## Included demos

### [Integration Reliability Acceptance Pack](INTEGRATION_RELIABILITY_ACCEPTANCE_PACK.md)

A buyer-facing scope for one paid discovery and control-plane slice. It names
the required buyer inputs, deliverables, hostile acceptance tests, human
approval boundary, and explicit exclusions before any production activation.

### [Український capability brief](CAPABILITY_UA.md)

Коротка українська подача: оплачуваний перший slice, exact public proof і
чітка доказова межа без production-обіцянок.

### Evidence gate

Turns structured evidence into `draft | escalate | hold`. Missing, stale,
conflicting, or insufficiently independent evidence is held. High-risk work
returns an explicit human-escalation state; it performs no network or external
action.

### Async polling contract

Models the control plane for `submit → persist id → poll → complete/fail`.
It proves fingerprint idempotency, bounded backoff, hard timeout, single-writer
atomic status-file replacement, and fail-closed behavior for crashes and
unknown IDs. It does not claim multi-writer persistence safety.

The worker is intentionally fake: this is not a ComfyUI, GPU, n8n, or
production deployment claim.

### [Operating-core composition demo](operating-core-demo/README.md)

Composes the checked-in evidence gate, bounded fake lifecycle, and EGOH owner
APIs into one frozen synthetic chain. Only `draft` enters the lifecycle; only
exact `complete` reaches a local `review-required` handoff. All other paths
hold with zero effects and no authority. It is a local reference, not a
provider, production, delivery, or external-action claim.

### [Evidence-Gated Operator Handoff](egoh-demo/README.md)

A synthetic, local-only contract that accepts a narrowly shaped evidence packet
only into `review-required`. Digest mismatch, stale evidence, unknown tools,
unexpected raw fields, ambiguous local targets, journal tampering, and a
caller-supplied decision all fail closed. The demo has no browser, network,
provider, credential, submit, or payment interface.

The included [public proof pack](egoh-demo/public-pack/TEST_RESULTS.md) records
the current hostile acceptance readback, fixture digests, a redacted example
handoff, and explicit non-production limits. It is an inspection artifact, not
a deployment claim.

## One-command proof

```bash
python3 run_proof.py
```

The checked-in Python implementations use only the Python standard library and
no installed packages. The proof command requires Python 3.12 and Node 24.14.0:
Node runs the dependency-free browser-local explorer runtime test with its
built-in `vm`, not npm or installed JavaScript packages. The runner prevents
Python bytecode writes; CI provisions those runtimes and runs the same command.

## Why this exists

AI-assisted automation becomes dangerous when orchestration code silently
promotes missing evidence, duplicate work, retry storms, or malformed output
into success. These examples make the decision and failure boundaries explicit
and reviewable.

## License

Published for portfolio review. No reuse license is granted at this stage.

## Author

Artur Onysko — AI automation builder for agent workflows, API integrations,
context and memory systems, and reliability boundaries.

See [PROFILE.md](PROFILE.md) for the working profile and evidence boundaries.
