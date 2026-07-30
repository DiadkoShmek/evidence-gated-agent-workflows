# Fake ComfyUI async polling contract

Small, standard-library-only evidence for a proposed **n8n → async image worker
→ poll → persist** control loop.  It is local and deterministic.

```bash
cd async-polling-contract
python3 -m unittest -v
python3 demo.py
```

The first command exercises the contract.  The second writes a local
`demo-status.json` receipt and prints it.  Delete that generated receipt when
it is no longer useful; it is not source evidence.

## Contract proved

1. A fingerprint is idempotent: repeat submission returns the original fake
   prompt id.
2. Status is persisted by fingerprint after every terminal outcome.
3. Polls have a hard attempt ceiling and planned exponential backoff.  The demo
   records delays; it never sleeps.
4. It fails closed for an unknown prompt id, an upstream crash, an explicit
   upstream failure, and a deadline timeout.

## Deliberate limits

- `FakeComfyUI` is not ComfyUI and makes no HTTP calls.
- There is no n8n installation or workflow JSON: claiming import compatibility
  without validating against a specific n8n version and real endpoint schema
  would be false.
- Backoff delays are a controller contract, not a live scheduler guarantee.
- This does not prove GPU execution, ComfyUI custom nodes, image quality, or
  production credentials/secrets handling.
