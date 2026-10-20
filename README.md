# Evidence-gated Agent Workflows

Small, runnable examples of automation that **stops when evidence is missing or conflicting**, explains why, and leaves the next decision with a person.

**[Explore the project →](https://diadkoshmek.github.io/evidence-gated-agent-workflows/en.html)** · [Українською](https://diadkoshmek.github.io/evidence-gated-agent-workflows/)

## Start here

```bash
python3 run_proof.py
```

Use **Python 3.12 and Node 24.14.0**, matching CI. The Python implementations use the Python standard library and
no installed packages. Node tests the browser-local explorer with its
built-in `vm`, not npm or installed JavaScript packages.

## Examples

| Example | What it checks |
|---|---|
| [Evidence gate](evidence-gate/README.md) | Missing, stale or conflicting evidence produces an explicit hold; high-risk work escalates. |
| [Async polling contract](async-polling-contract/README.md) | Submit, retain an ID, poll with bounded backoff, and handle completion or failure. |
| [Operating-core composition](operating-core-demo/README.md) | One synthetic chain from evidence check to a local review handoff. |
| [Immutable artifact handoff](immutable-artifact-handoff-demo/README.md) | Bytes and a receipt remain bound across partial publication, digest conflict and namespace replacement. |
| [Agent action admission](agent-action-admission-demo/README.md) | A typed request must match the declared tool and simulator before local review. |
| [Bounded local-context review](bounded-rag-review/README.md) | Exact local source identities and deterministic lexical matching produce `local-context-review-ready` metadata. |
| [Operator handoff](egoh-demo/README.md) | A narrow evidence packet reaches `review-required`; stale, malformed or conflicting input is refused. |

All examples use **synthetic inputs and local effects**. No real provider calls, authenticated approvals or production deployments are demonstrated. Passing the tests establishes these fixtures, not safety for another system.

## Inspect the evidence

[Architecture](https://diadkoshmek.github.io/evidence-gated-agent-workflows/architecture.html) · [Case study](https://diadkoshmek.github.io/evidence-gated-agent-workflows/case-study.html) · [Proof pack](egoh-demo/public-pack/TEST_RESULTS.md)

The proof pack contains fixture identities, checked outcomes and limits. The source and CI use the same proof command.

## Author and use

Artur Onysko, working with AI tools. [Profile and contact](https://github.com/DiadkoShmek).

Published for portfolio review. No reuse license is granted at this stage.
