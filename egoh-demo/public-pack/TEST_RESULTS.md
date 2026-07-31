# EGOH demo — локальний результат тестів

**Статус:** prepared for publication, **not published**.  
**Runtime checked:** Python 3.13.7.

## Exact acceptance command

```bash
cd egoh-demo
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v tests.test_egoh_demo
```

## Readback

```text
test_01_valid_synthetic_evidence_is_non_effecting_handoff ... ok
test_02_missing_or_unexpected_fields_hold_without_handoff ... ok
test_03_altered_evidence_digest_is_held ... ok
test_04_stale_evidence_is_held ... ok
test_05_unknown_tool_is_denied_before_handoff ... ok
test_06_content_free_contract_rejects_extra_raw_field ... ok
test_07_loopback_target_boundary_rejects_wrong_or_ambiguous_input ... ok
test_08_exact_replay_is_idempotent ... ok
test_09_journal_tamper_fails_closed ... ok
test_10_handoff_is_redacted_and_requires_human_action ... ok
test_11_effect_counters_and_import_surface_are_zero_and_local ... ok
test_12_caller_cannot_supply_or_mint_a_decision ... ok
test_13_no_candidate_is_held_by_derived_policy ... ok
test_14_cli_rejects_arbitrary_journal_path ... ok
test_15_direct_api_rejects_raw_outside_path ... ok
test_16_owned_journal_rejects_symlink_leaf_ancestor_and_traversal ... ok

----------------------------------------------------------------------
Ran 16 tests in 0.012s

OK
```

This is an acceptance readback for the current synthetic local reference. It is
not a production certification or independent audit.

## Exact example command

```bash
cd egoh-demo
PYTHONDONTWRITEBYTECODE=1 python3 run_demo.py --scenario valid-review
```

The result is `review-required`, never `handoff-ready`, and all effect counters
remain zero. The CLI always writes its journal inside a temporary directory and
does not accept an output-path argument. The checked-in [redacted handoff](example-valid-review.handoff.json)
and [one-event journal](example-valid-review.journal.jsonl) are generated from
the synthetic `valid-review` fixture.

## Verify the checked-in artifacts

```bash
cd egoh-demo/public-pack
sha256sum -c FIXTURES.sha256
python3 -m json.tool example-valid-review.handoff.json >/dev/null
PYTHONPATH=.. python3 -c 'from pathlib import Path; from egoh_demo import read_journal; assert len(read_journal(Path("example-valid-review.journal.jsonl"))) == 1; print("journal: OK")'
```
