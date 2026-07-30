# Local Proof Receipt

**Date:** 30 July 2026
**Scope:** local deterministic demo only.

## Commands

```bash
python3 -m py_compile src/evidence_gate.py scripts/stress.py tests/test_evidence_gate.py
python3 -m unittest -v tests/test_evidence_gate.py
python3 -m src.evidence_gate --input fixtures/clean.json --as-of 2026-07-30T12:00:00Z
python3 scripts/stress.py --iterations 1000
```

## Readback

- unit tests: `11/11 OK`;
- clean fixture: `draft / EVIDENCE_COMPLETE`;
- `external_action_authorized=false`;
- stress: `PASS`;
- fixture families: `5`;
- iterations: `1000`;
- evaluation runs: `5000`;
- elapsed: approximately `0.20s` on the proof host;
- trace digest: `0eaf9f56200f53a9309781bf7903b6533b96db6a9355255fddc69c2d26ac4b7b`;
- network/model/external action: `false`.

Timing is an observation from one local machine, not a performance guarantee.
