# Evidence-gated Agent Workflows

Two small, dependency-free Python references for automation systems that must
fail honestly instead of inventing a successful result.

For clients: this demonstrates how I make AI workflows observable and honest
about failure before they are connected to real systems.

## Included demos

### Evidence gate

Turns structured evidence into `draft | escalate | hold`. Missing, stale,
conflicting, or insufficiently independent evidence is held. High-risk work is
escalated to human authority. It performs no network or external action.

### Async polling contract

Models the control plane for `submit → persist id → poll → complete/fail`.
It proves fingerprint idempotency, bounded backoff, hard timeout, single-writer
atomic status-file replacement, and fail-closed behavior for crashes and
unknown IDs. It does not claim multi-writer persistence safety.

The worker is intentionally fake: this is not a ComfyUI, GPU, n8n, or
production deployment claim.

## One-command proof

```bash
python3 run_proof.py
```

The repository uses only the Python standard library. CI runs the same command.

## Why this exists

AI-assisted automation becomes dangerous when orchestration code silently
promotes missing evidence, duplicate work, retry storms, or malformed output
into success. These examples make the decision and failure boundaries explicit
and reviewable.

## License

Published for portfolio review. No reuse license is granted at this stage.

## Author

Artur Onysko — AI automation builder for agent workflows, API integrations,
context and memory systems, and reliability boundaries.

See [PROFILE.md](PROFILE.md) for the working profile and evidence boundaries.
