from __future__ import annotations

import copy
import hashlib
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import agent_action_admission as admission


NOW = datetime(2026, 8, 12, 0, 30, tzinfo=timezone.utc)


def request(action_id: str = "ticket-action-1") -> dict:
    return {
        "schema": admission.REQUEST_SCHEMA,
        "action_id": action_id,
        "tool": {"name": "set-ticket-priority", "schema_version": "1", "arguments": {"priority": "high", "ticket_id": "T-101"}},
        "pre_state": {"priority": "normal", "ticket_id": "T-101"},
    }


def review(commitment: admission.Commitment) -> dict:
    return {
        "schema": admission.REVIEW_SCHEMA,
        "action_id": commitment.action_id,
        "commitment_sha256": commitment.commitment_sha256,
        "decision": "approve-simulation-only",
        "reviewer_class": "synthetic-caller-attested-fixture",
        "observed_at": "2026-08-12T00:00:00Z",
        "expires_at": "2026-08-12T01:00:00Z",
        "claims": {"human_authenticated": False, "provider_observed": False, "external_effect_authorized": False},
    }


def raw(value: object) -> bytes:
    return admission.canonical_json(value).encode("utf-8")


class AgentActionAdmissionTests(unittest.TestCase):
    def test_valid_request_commits_before_raw_free_simulation_receipt(self) -> None:
        owner = admission.CommitmentOwner()
        commitment, replayed = owner.commit(raw(request()))
        self.assertFalse(replayed)
        receipt = admission.simulate_for_review(owner, commitment, raw(review(commitment)), now=NOW)
        self.assertEqual(receipt["status"], "review-required")
        self.assertEqual(receipt["authority"], {"human_authenticated": False, "provider_observed": False, "network": False, "external_effect": False})
        self.assertEqual(receipt["effect_counters"], {"tool_calls": 0, "network_calls": 0, "provider_mutations": 0, "external_writes": 0})
        rendered = admission.canonical_json(receipt)
        self.assertNotIn("T-101", rendered)
        self.assertNotIn("priority\"", rendered)

    def test_exact_replay_is_idempotent_and_conflicting_identity_holds(self) -> None:
        owner = admission.CommitmentOwner()
        first, replayed = owner.commit(raw(request()))
        second, replayed_second = owner.commit(raw(request()))
        self.assertFalse(replayed)
        self.assertTrue(replayed_second)
        self.assertIs(first, second)
        changed = request()
        changed["tool"]["arguments"]["priority"] = "low"
        with self.assertRaisesRegex(admission.AdmissionError, "action-identity-conflict"):
            owner.commit(raw(changed))

    def test_caller_held_snapshot_restores_replay_and_simulation_after_restart(self) -> None:
        owner = admission.CommitmentOwner()
        original, _ = owner.commit(raw(request()))
        snapshot = owner.export_snapshot()

        restored = admission.CommitmentOwner.restore_snapshot(snapshot)
        current, replayed = restored.commit(raw(request()))
        self.assertTrue(replayed)
        self.assertEqual(current.public(), original.public())
        receipt = admission.simulate_for_review(
            restored,
            current,
            raw(review(current)),
            now=NOW,
        )
        self.assertEqual(receipt["commitment_sha256"], original.commitment_sha256)
        self.assertNotIn("T-101", admission.canonical_json(receipt))

    def test_snapshot_rejects_tamper_duplicate_reorder_and_contract_drift(self) -> None:
        owner = admission.CommitmentOwner()
        owner.commit(raw(request("action-a")))
        owner.commit(raw(request("action-b")))
        snapshot = owner.export_snapshot()
        decoded = admission._load_canonical_json_bounded(
            snapshot,
            "test-invalid",
            admission.MAX_OWNER_SNAPSHOT_BYTES,
        )

        tampered = copy.deepcopy(decoded)
        tampered["commitments"][0]["request_hex"] = raw(request("action-b")).hex()
        tampered_payload = {key: value for key, value in tampered.items() if key != "snapshot_sha256"}
        tampered["snapshot_sha256"] = admission.sha256_json(tampered_payload)
        reordered = copy.deepcopy(decoded)
        reordered["commitments"].reverse()
        reordered_payload = {key: value for key, value in reordered.items() if key != "snapshot_sha256"}
        reordered["snapshot_sha256"] = admission.sha256_json(reordered_payload)
        drifted = copy.deepcopy(decoded)
        drifted["simulator_contract_sha256"] = "f" * 64
        drifted_payload = {key: value for key, value in drifted.items() if key != "snapshot_sha256"}
        drifted["snapshot_sha256"] = admission.sha256_json(drifted_payload)

        cases = (
            (snapshot[:-1] + b' ,"schema":"agent-action-owner-snapshot-v1"}', "json-duplicate-key"),
            (raw(tampered), "commitment-mutated"),
            (raw(reordered), "owner-snapshot-order-invalid"),
            (raw(drifted), "owner-snapshot-simulator-drift"),
        )
        for packet, reason in cases:
            with self.subTest(reason=reason), self.assertRaisesRegex(admission.AdmissionError, reason):
                admission.CommitmentOwner.restore_snapshot(packet)

    def test_snapshot_owner_count_is_bounded_before_export(self) -> None:
        owner = admission.CommitmentOwner()
        for index in range(admission.MAX_OWNER_SNAPSHOT_COMMITMENTS + 1):
            owner.commit(raw(request(f"bounded-{index}")))
        with self.assertRaisesRegex(admission.AdmissionError, "owner-snapshot-commitments-invalid"):
            owner.export_snapshot()

    def test_noncanonical_duplicate_extra_and_unknown_tool_hold(self) -> None:
        canonical = raw(request())
        with self.assertRaisesRegex(admission.AdmissionError, "json-noncanonical"):
            admission.CommitmentOwner().commit(b'{"schema":"synthetic-agent-action-request-v1", "action_id":"x"}')
        duplicate = canonical[:-1] + b',"schema":"synthetic-agent-action-request-v1"}'
        with self.assertRaisesRegex(admission.AdmissionError, "json-duplicate-key"):
            admission.CommitmentOwner().commit(duplicate)
        extra = request()
        extra["authority"] = True
        with self.assertRaisesRegex(admission.AdmissionError, "request-schema-invalid"):
            admission.CommitmentOwner().commit(raw(extra))
        unknown = request()
        unknown["tool"]["name"] = "send-email"
        with self.assertRaisesRegex(admission.AdmissionError, "tool-unknown"):
            admission.CommitmentOwner().commit(raw(unknown))

    def test_tool_version_arguments_prestate_and_noop_are_strict(self) -> None:
        cases = []
        changed = request(); changed["tool"]["schema_version"] = "2"; cases.append((changed, "tool-version-invalid"))
        changed = request(); changed["tool"]["arguments"]["extra"] = 1; cases.append((changed, "tool-arguments-invalid"))
        changed = request(); changed["pre_state"]["ticket_id"] = "T-999"; cases.append((changed, "ticket-identity-invalid"))
        changed = request(); changed["pre_state"]["priority"] = "high"; cases.append((changed, "transition-noop"))
        for value, reason in cases:
            with self.subTest(reason=reason), self.assertRaisesRegex(admission.AdmissionError, reason):
                admission.CommitmentOwner().commit(raw(value))

    def test_foreign_expired_and_authority_claiming_review_hold(self) -> None:
        owner = admission.CommitmentOwner()
        commitment, _ = owner.commit(raw(request()))
        foreign = review(commitment); foreign["commitment_sha256"] = "0" * 64
        expired = review(commitment); expired["expires_at"] = "2026-08-12T00:01:00Z"
        authority = review(commitment); authority["claims"]["human_authenticated"] = True
        for value, reason in ((foreign, "review-binding-invalid"), (expired, "review-expired"), (authority, "review-authority-invalid")):
            with self.subTest(reason=reason), self.assertRaisesRegex(admission.AdmissionError, reason):
                admission.simulate_for_review(owner, commitment, raw(value), now=NOW)

    def test_unowned_or_forged_commitment_cannot_simulate(self) -> None:
        owner = admission.CommitmentOwner()
        commitment, _ = owner.commit(raw(request()))
        other = admission.CommitmentOwner()
        with self.assertRaisesRegex(admission.AdmissionError, "commitment-not-current"):
            other.require_current(commitment)
        forged = copy.copy(commitment)
        with self.assertRaisesRegex(admission.AdmissionError, "commitment-not-current"):
            admission.simulate_for_review(owner, forged, raw(review(forged)), now=NOW)
        foreign_owner = admission.CommitmentOwner()
        foreign, _ = foreign_owner.commit(raw(request("foreign-action")))
        owner._by_action_id[foreign.action_id] = foreign
        with self.assertRaisesRegex(admission.AdmissionError, "commitment-not-current"):
            admission.simulate_for_review(owner, foreign, raw(review(foreign)), now=NOW)

    def test_terminal_rederivation_rejects_mutated_request_and_matching_digest(self) -> None:
        owner = admission.CommitmentOwner()
        commitment, _ = owner.commit(raw(request()))
        changed = request()
        changed["pre_state"]["priority"] = "low"
        changed_raw = raw(changed)
        object.__setattr__(commitment, "_request_bytes", changed_raw)
        object.__setattr__(commitment, "request_sha256", hashlib.sha256(changed_raw).hexdigest())
        with self.assertRaisesRegex(admission.AdmissionError, "commitment-mutated"):
            admission.simulate_for_review(owner, commitment, raw(review(commitment)), now=NOW)

    def test_request_and_simulator_drift_hold_before_receipt(self) -> None:
        owner = admission.CommitmentOwner()
        commitment, _ = owner.commit(raw(request()))
        original = admission.SIMULATOR_CONTRACT_SHA256
        with mock.patch.object(admission, "SIMULATOR_CONTRACT_SHA256", "f" * 64):
            with self.assertRaisesRegex(admission.AdmissionError, "commitment-mutated"):
                admission.simulate_for_review(owner, commitment, raw(review(commitment)), now=NOW)
        self.assertEqual(admission.SIMULATOR_CONTRACT_SHA256, original)
        changed_manifest = copy.deepcopy(admission.TOOL_MANIFEST)
        changed_manifest["schema_version"] = "2"
        with mock.patch.object(admission, "TOOL_MANIFEST", changed_manifest):
            with self.assertRaisesRegex(admission.AdmissionError, "commitment-mutated"):
                admission.simulate_for_review(owner, commitment, raw(review(commitment)), now=NOW)
        with mock.patch.object(admission, "_expected_state", return_value={"ticket_id": "T-101", "priority": "low"}):
            with self.assertRaisesRegex(admission.AdmissionError, "commitment-mutated"):
                admission.simulate_for_review(owner, commitment, raw(review(commitment)), now=NOW)

    def test_review_window_is_bounded(self) -> None:
        owner = admission.CommitmentOwner()
        commitment, _ = owner.commit(raw(request()))
        too_long = review(commitment)
        too_long["expires_at"] = "2026-08-12T01:00:01Z"
        with self.assertRaisesRegex(admission.AdmissionError, "review-expired"):
            admission.simulate_for_review(owner, commitment, raw(too_long), now=NOW)

    def test_convenience_run_holds_without_receipt(self) -> None:
        result = admission.run(raw({"schema": "wrong"}), raw({}), now=NOW)
        self.assertEqual(result["status"], "held")
        self.assertFalse(result["external_effect"])
        self.assertIsNone(result["receipt"])

    def test_import_surface_has_no_effect_capability(self) -> None:
        source = Path(admission.__file__).read_text(encoding="utf-8")
        for forbidden in ("import socket", "import subprocess", "urllib", "requests", "http.client", "os.system", "Popen("):
            self.assertNotIn(forbidden, source)
        self.assertEqual(hashlib.sha256(admission.SIMULATOR_CONTRACT.encode("ascii")).hexdigest(), admission.SIMULATOR_CONTRACT_SHA256)


if __name__ == "__main__":
    unittest.main()
