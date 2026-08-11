# Immutable artifact handoff

This standard-library-only reference publishes synthetic artifact bytes first
and a canonical receipt last. The loader holds nofollow descriptors across the
root, ancestors, bundle directory, receipt, and artifact, then revalidates
terminal bytes and inode identity before returning a metadata-only
`review-required` handoff.

Run it:

```bash
python3 -m unittest discover -s tests -v
python3 run_demo.py
```

The hostile suite covers missing and partial publication, strict JSON/schema
drift, digest conflict, symlinked namespaces, replaced roots/parents/leaves,
same-byte inode swaps, in-place mutation, short reads, exact replay, conflicting
existing leaves, concurrent publishers, and invalid source input.

The fixture is synthetic and local. It performs no network, provider, model,
deployment, payment, send, or external-effect action and does not establish
production safety or multi-owner tamper resistance.
