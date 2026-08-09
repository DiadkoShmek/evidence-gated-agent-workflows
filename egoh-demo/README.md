# Evidence-Gated Operator Handoff demo

This is a local, synthetic Python reference for a narrow decision boundary:
valid evidence can reach only `review-required`; it cannot mint a ready action.

The module uses the Python standard library only. It has no network, browser,
provider, credential, submit, payment, or delivery interface. Its JSONL journal
is a single-process synthetic audit demo, not multi-writer or tamper-resistant
storage. Importable write APIs accept only an `OwnedJournal` minted beneath an
existing caller-owned directory; raw paths, traversal, and symlink targets are
rejected.

## Run

```bash
python3 -m unittest -v tests.test_egoh_demo
python3 run_demo.py --scenario valid-review
```

The first command exercises the hostile paths. The second prints a redacted
local handoff with zero effect counters. `review-required` is not a submission,
delivery, contract, income, or production-ready state.

## Proof pack

The checked-in [public-pack](public-pack/TEST_RESULTS.md) contains:

- an exact `16/16` acceptance-suite readback;
- SHA-256 checksums for all synthetic fixtures;
- a redacted `valid-review` handoff and one-event JSONL journal;
- explicit [non-production limits](public-pack/LIMITS.md).

Everything in this directory is synthetic and locally reviewable. Nothing here
is a defense deployment or an authorization to perform an external action.
