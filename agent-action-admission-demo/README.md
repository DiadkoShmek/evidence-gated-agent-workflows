# Agent action admission

This dependency-free synthetic demo binds one typed action request, its exact
pre-state, the checked-in tool manifest, and a deterministic simulator contract
into a pre-effect commitment **before** simulation.

Only an exact, time-bounded synthetic review fixture bound to that commitment
allows the pure simulator to run. The result is a raw-free
`review-required` receipt. It never calls the named tool and grants no human,
provider, network, filesystem, deployment, or external-effect authority.

```bash
python3 -m unittest discover -s tests -v
python3 run_demo.py
```

The hostile proof rejects malformed or non-canonical JSON, duplicate keys,
unknown tools, schema or argument drift, action-identity conflict, foreign or
expired review fixtures, caller-supplied authority, unowned commitments,
simulator drift, and transition mismatch.

This proves correspondence only to the checked-in synthetic transition model.
It does not prove a real tool, real target state, authenticated approval,
execution safety, delivery, idempotent external effects, or provider truth. A
client adapter needs its own source, target, identity, authority, and uncertain
effect contract. The V1 owner and replay identity are process-local and vanish
on restart; the demo trusts its current Python process and is not a sandbox
against code that deliberately mutates private in-process state.
