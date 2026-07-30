# Limits

## Implemented

- strict structured input;
- freshness, conflict, and independence checks;
- `draft | escalate | hold` decision;
- evidence and input hashes;
- deterministic replay;
- zero external-action surface.

## Tested

- clean, missing, stale, conflict, risk, insufficient-independence, unknown-field, deterministic, and timezone cases;
- bounded repeated fixture stress.

## Not implemented

- web crawling or source authentication;
- database, queue, CRM, inbox, or model integration;
- human-label quality evaluation;
- authorization, message delivery, refund, payment, or account mutation;
- distributed execution or internet-scale performance.

## External dependencies

None. Python 3.11+ standard library only.

## Future work

- JSON Schema publication;
- signed source receipts;
- policy/version manifest;
- separate approval-gated transport adapter;
- held-out evaluation with an authorized real-data owner.
