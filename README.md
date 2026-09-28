# Evidence-gated Agent Workflows

**Українською:** тут є невеликі приклади AI-процесів, які зупиняються,
коли даних бракує або вони суперечать одне одному. Код і тести відкриті;
[сторінка проєкту](https://diadkoshmek.github.io/evidence-gated-agent-workflows/)
пояснює ідею без потреби читати весь репозиторій.

Small, dependency-free examples of a problem that is easy to miss: an
automation receives incomplete or conflicting information and carries on as
if it succeeded. These demos stop, give a reason, and leave the decision with
a person.

**Try the examples:** `python3 run_proof.py` (Python 3.12 and Node 24.14.0).
The short descriptions below explain what each example checks.

Everything here uses synthetic inputs and local effects. Passing the tests
does not establish production readiness or safety for another system.

## Included demos

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

### [Immutable artifact handoff](immutable-artifact-handoff-demo/README.md)

Publishes synthetic artifact bytes first and a canonical receipt last, then
loads the bundle through held nofollow descriptors before producing a local
`review-required` handoff. Missing receipts, namespace replacement, symlinks,
digest conflict, partial publication, replay conflict, and concurrent writers
fail closed. It proves this checked-in local fixture only—not a deployment,
provider, model, trading, or external-effect boundary.

### [Agent action admission](agent-action-admission-demo/README.md)

Commits one strict typed action request, exact pre-state, tool manifest and
simulator contract before a fixed pure transition model runs. Unknown tools,
identity conflict, schema or argument drift, foreign/expired review fixtures,
caller-supplied authority and simulator mismatch hold without a receipt. The
result is raw-free `review-required` metadata with every real effect counter at
zero—not a real tool call, authenticated approval, or execution-safety claim.

### [Bounded local-context review](bounded-rag-review/README.md)

Binds synthetic local source text to exact SHA-256 identities, ranks it by
deterministic lexical overlap, and exposes only raw-free source metadata for a
local `local-context-review-ready` result. Irrelevant queries, digest
conflicts, duplicate sources, noncanonical requests and every non-review
effect hold. This is not semantic
RAG quality, an LLM answer, a vector database, or a production retrieval claim.

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

Artur Onysko. See [my profile](https://github.com/DiadkoShmek) for other
projects and a way to get in touch.
