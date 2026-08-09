# EGOH public-pack limits

## What this is

A local synthetic reference for an evidence-gated decision and human handoff.
Validated synthetic evidence can reach only `review-required`.

## What this is not

- Not a production system: no SLA, HA, access control, external integration, or independent security review.
- Not a defense deployment: no defense-network connection, operational data, field use, procurement, or authorization.
- Not a real application workflow: `review-required` is not a submission, delivery, contract, payment, or income.
- Not autonomous action: an external action requires separate named human authority and provider-side readback outside this demo.

## Process and storage boundary

- **Single process only.** The JSONL journal has no locking, multi-writer coordination, or tamper-resistant storage. Public write APIs require an `OwnedJournal` minted under an existing current-user-owned root and reject raw paths, traversal, and symlink leaf or ancestor paths.
- **Synthetic fixtures only.** There is no page content, recipient, credential, token, cookie, API secret, or personal data in this package.
- **No independent audit claim.** The `16/16` result is the repository acceptance suite, not a certification or penetration test.

## External-effect boundary

```text
network_calls=0
browser_writes=0
provider_mutations=0
submissions=0
payments=0
external_action=false
```

Any future connection to a browser, email, ATS, payment provider, or government
system would be a different product requiring a separate threat model,
authorization, and proof. It does not follow from this demo.

## Publication state

This folder is a review candidate only. It has not been pushed, hosted, sent,
or connected to an external provider by this package.
