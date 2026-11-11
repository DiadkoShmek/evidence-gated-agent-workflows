# Evidence-gated Agent Workflows

<picture>
  <source media="(prefers-color-scheme: dark) and (max-width: 600px)" srcset="https://raw.githubusercontent.com/DiadkoShmek/DiadkoShmek/main/assets/identity/workflows-dark-mobile.svg">
  <source media="(max-width: 600px)" srcset="https://raw.githubusercontent.com/DiadkoShmek/DiadkoShmek/main/assets/identity/workflows-light-mobile.svg">
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/DiadkoShmek/DiadkoShmek/main/assets/identity/workflows-dark.svg">
  <img src="https://raw.githubusercontent.com/DiadkoShmek/DiadkoShmek/main/assets/identity/workflows-light.svg" alt="Evidence-gated Agent Workflows — executable references" width="1280">
</picture>

Small, runnable examples of automation that **stops when evidence is missing or conflicting**, explains why, and leaves the next decision with a person.

**[Try the interactive demo](https://diadkoshmek.github.io/evidence-gated-agent-workflows/en.html)** · [Українською](https://diadkoshmek.github.io/evidence-gated-agent-workflows/) · [See the proof pack](egoh-demo/public-pack/TEST_RESULTS.md)

## Run the checks locally

```bash
python3 run_proof.py
```

Use **Python 3.12 and Node 24.14.0**, matching CI. The Python implementations use the Python standard library and
no installed packages. Node tests the browser-local explorer with its
built-in `vm`, not npm or installed JavaScript packages.

## Examples

- **[Evidence gate](evidence-gate/README.md)** · Missing, stale or conflicting evidence produces an explicit hold; high-risk work escalates.
- **[Async polling contract](async-polling-contract/README.md)** · Submit, retain an ID, poll with bounded backoff, and handle completion or failure.
- **[Operating-core composition](operating-core-demo/README.md)** · One synthetic chain from evidence check to a local review handoff.
- **[Immutable artifact handoff](immutable-artifact-handoff-demo/README.md)** · Bytes and a receipt remain bound across partial publication, digest conflict and namespace replacement.
- **[Agent action admission](agent-action-admission-demo/README.md)** · A typed request must match the declared tool and simulator before local review.
- **[Bounded local-context review](bounded-rag-review/README.md)** · Exact local source identities and deterministic lexical matching produce `local-context-review-ready` metadata.
- **[Operator handoff](egoh-demo/README.md)** · A narrow evidence packet reaches `review-required`; stale, malformed or conflicting input is refused.

All examples use **synthetic inputs and local effects**. No real provider calls, authenticated approvals or production deployments are demonstrated. Passing the tests establishes these fixtures, not safety for another system.

## Inspect the evidence

[Architecture](https://diadkoshmek.github.io/evidence-gated-agent-workflows/architecture.html) · [Case study](https://diadkoshmek.github.io/evidence-gated-agent-workflows/case-study.html)

The proof pack contains fixture identities, checked outcomes and limits. The source and CI use the same proof command.

## Project and use

AI-assisted engineering by DiadkoShmek. [Project index](https://github.com/DiadkoShmek) · [External results](https://github.com/DiadkoShmek/engineering-results/blob/main/README.en.md).

Published for portfolio review. No reuse license is granted at this stage.
