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

The owner can export one canonical private continuity packet and restore it in
a fresh Python process. Exact requests then replay to the same commitment and
the time-bounded review can still drive the same pure simulation. Packet
tampering, duplicate JSON keys, reordered identities, request drift, and tool
or simulator version drift all hold before a receipt. The packet contains the
synthetic request bytes and must remain private.

This proves correspondence only to the checked-in synthetic transition model.
It does not prove a real tool, real target state, authenticated approval,
execution safety, delivery, idempotent external effects, or provider truth. A
client adapter needs its own source, target, identity, authority, and uncertain
effect contract. Restart continuity is caller-held and integrity-checked, not
authenticated storage: a trusted caller can construct a different internally
consistent packet. The live owner remains process-local after restore, and the
demo is not a sandbox against code that deliberately mutates private
in-process state.

Have a real agent result that must not silently become an internal tool action?
[Map that one boundary to a browser-local review draft](https://diadkoshmek.github.io/evidence-gated-agent-workflows/en.html#intake),
then manually select **Agent result to internal tool**. The page does not copy
this synthetic fixture, prefill the public Issue Form, or submit anything.
