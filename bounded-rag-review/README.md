# Bounded local-context review

This dependency-free capsule proves one narrow retrieval boundary:

`source text + SHA-256 -> deterministic lexical ranking -> local-context-review-ready | held`

It accepts only canonical duplicate-free JSON and exact source families. Source
IDs and contents must be unique, every digest is recomputed, ranking is
deterministic, and non-review effects return no retrieved context. Output is
raw-free metadata containing source IDs, source hashes and overlap counts.

```bash
python3 -m unittest -v test_bounded_rag_review.py
python3 run_demo.py
```

`local-context-review-ready` means only that checked-in local source text has
exact lexical overlap with the local query and may be inspected by a reviewer.
It does not prove semantic retrieval quality, an LLM answer, vector-database
behavior, customer-data safety, authenticated human approval, production
readiness, provider observation, or authority for an external effect. The
module imports no network, process, storage, vector, or agent-framework API.
