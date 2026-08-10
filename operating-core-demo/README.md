# Operating-core composition demo

This local, standard-library-only reference composes the existing checked-in
owners in one synthetic chain:

`frozen boundary input → evidence draft → bounded fake lifecycle → EGOH review-required handoff`

The evidence gate must decide exactly `draft` before the lifecycle is created.
The lifecycle must end exactly `complete` before the typed EGOH observation is
decided and journaled. Every other state is `held` without a handoff.

```bash
cd operating-core-demo
python3 -m unittest -v tests.test_operating_core_demo
python3 run_demo.py
```

The fixture and output are synthetic. The demo has no network, browser,
provider, send, credential, payment, production, or external-action interface.
Its only write surfaces are the existing async status store and EGOH journal,
both created inside an exact module-owned temporary directory and removed before
the public call returns. `review-required` is not delivery, approval, contract,
income, or production readiness.
