#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone

from agent_action_admission import COMMITMENT_SCHEMA, REVIEW_SCHEMA, CommitmentOwner, canonical_json, simulate_for_review


def main() -> None:
    request = {
        "schema": "synthetic-agent-action-request-v1",
        "action_id": "ticket-priority-demo-1",
        "tool": {"name": "set-ticket-priority", "schema_version": "1", "arguments": {"priority": "high", "ticket_id": "T-101"}},
        "pre_state": {"priority": "normal", "ticket_id": "T-101"},
    }
    owner = CommitmentOwner()
    commitment, replayed = owner.commit(canonical_json(request).encode("utf-8"))
    assert commitment.schema == COMMITMENT_SCHEMA
    review = {
        "schema": REVIEW_SCHEMA,
        "action_id": request["action_id"],
        "commitment_sha256": commitment.commitment_sha256,
        "decision": "approve-simulation-only",
        "reviewer_class": "synthetic-caller-attested-fixture",
        "observed_at": "2026-08-12T00:00:00Z",
        "expires_at": "2026-08-12T01:00:00Z",
        "claims": {"human_authenticated": False, "provider_observed": False, "external_effect_authorized": False},
    }
    receipt = simulate_for_review(
        owner,
        commitment,
        canonical_json(review).encode("utf-8"),
        now=datetime(2026, 8, 12, 0, 30, tzinfo=timezone.utc),
    )
    print(json.dumps({"status": receipt["status"], "commitment_replayed": replayed, "receipt": receipt}, sort_keys=True))


if __name__ == "__main__":
    main()
