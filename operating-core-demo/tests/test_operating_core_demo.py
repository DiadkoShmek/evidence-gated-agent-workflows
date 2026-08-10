from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import operating_core_demo  # noqa: E402
from operating_core_demo import _run_boundary_in_directory, content_hash, run_boundary, zero_effect_counters  # noqa: E402
from egoh_demo import JournalOwner, read_journal, sha256_json  # noqa: E402


FIXTURE = ROOT / "fixtures" / "clean-complete.json"


def boundary() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class TickClock:
    def __init__(self, ticks: list[int]) -> None:
        self._ticks = iter(ticks)

    def __call__(self) -> int:
        return next(self._ticks)


class OperatingCoreDemoTests(unittest.TestCase):
    def assert_zero_effect_boundary(self, result: dict) -> None:
        self.assertEqual(result["effect_counters"], zero_effect_counters())
        self.assertEqual(
            (result["authority"], result["external_action"], result["provider"], result["provider_delivery_observed"], result["production"]),
            (False, False, False, False, False),
        )

    def test_clean_chain_reaches_only_review_required_with_zero_effects(self) -> None:
        result = run_boundary(boundary())
        self.assertEqual((result["decision"], result["reason"]), ("review-required", "synthetic-chain-complete"))
        self.assertEqual(result["evidence_decision"]["decision"], "draft")
        self.assertEqual(result["lifecycle"]["state"], "complete")
        self.assertEqual(result["egoh"]["decision"]["decision"], "review-required")
        self.assertFalse(result["egoh"]["journal"]["replayed"])
        self.assertIsNotNone(result["handoff"])
        self.assert_zero_effect_boundary(result)

    def test_evidence_hold_stops_before_lifecycle_and_handoff(self) -> None:
        raw = boundary()
        raw["evidence"]["facts"] = raw["evidence"]["facts"][:1]
        raw["evidence_sha256"] = content_hash(raw["evidence"])
        raw["lifecycle"]["fingerprint"] = f"operating-core:{raw['chain_id']}:{raw['evidence_sha256']}"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = _run_boundary_in_directory(raw, root)
            self.assertEqual(list(root.iterdir()), [])
        self.assertEqual((result["decision"], result["reason"]), ("held", "evidence-not-draft"))
        self.assertEqual(result["evidence_decision"]["decision"], "hold")
        self.assertIsNone(result["lifecycle"])
        self.assertIsNone(result["egoh"])
        self.assertIsNone(result["handoff"])
        self.assert_zero_effect_boundary(result)

    def test_failed_lifecycle_has_no_egoh_or_handoff(self) -> None:
        raw = boundary()
        raw["lifecycle"]["events"] = ["failed"]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = _run_boundary_in_directory(raw, root)
            self.assertTrue((root / "synthetic-status.json").is_file())
            self.assertFalse((root / "journal.jsonl").exists())
        self.assertEqual((result["decision"], result["reason"]), ("held", "lifecycle-not-complete"))
        self.assertEqual(result["lifecycle"]["state"], "failed")
        self.assertIsNone(result["egoh"])
        self.assertIsNone(result["handoff"])
        self.assert_zero_effect_boundary(result)

    def test_timed_out_lifecycle_has_no_egoh_or_handoff(self) -> None:
        raw = boundary()
        raw["lifecycle"]["events"] = ["queued"]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = _run_boundary_in_directory(raw, root, clock=TickClock([0, 10]))
            self.assertTrue((root / "synthetic-status.json").is_file())
            self.assertFalse((root / "journal.jsonl").exists())
        self.assertEqual(result["lifecycle"]["state"], "timed_out")
        self.assertEqual(result["lifecycle"]["attempts"], 0)
        self.assertIsNone(result["egoh"])
        self.assertIsNone(result["handoff"])
        self.assert_zero_effect_boundary(result)

    def test_exact_replay_reuses_the_existing_egoh_event(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = _run_boundary_in_directory(boundary(), root)
            second = _run_boundary_in_directory(boundary(), root)
            rows = read_journal(JournalOwner(root).journal())
        self.assertFalse(first["egoh"]["journal"]["replayed"])
        self.assertTrue(second["egoh"]["journal"]["replayed"])
        self.assertEqual(first["egoh"]["journal"]["event_sha256"], second["egoh"]["journal"]["event_sha256"])
        self.assertEqual(len(rows), 1)
        self.assert_zero_effect_boundary(first)
        self.assert_zero_effect_boundary(second)

    def test_strict_boundary_keys_and_identity_fail_before_any_write(self) -> None:
        cases: list[tuple[str, dict]] = []
        unknown = boundary()
        unknown["unexpected"] = "send"
        cases.append(("boundary-schema-invalid", unknown))
        altered = boundary()
        altered["evidence_sha256"] = "0" * 64
        cases.append(("boundary-evidence-digest-invalid", altered))
        wrong_lifecycle = boundary()
        wrong_lifecycle["lifecycle"]["fingerprint"] = "operating-core:other"
        cases.append(("boundary-lifecycle-identity-invalid", wrong_lifecycle))
        wrong_observation = boundary()
        wrong_observation["egoh_observation"]["scenario_id"] = "other"
        wrong_observation["egoh_observation"]["evidence"]["scenario_id"] = "other"
        wrong_observation["egoh_observation"]["evidence_sha256"] = sha256_json(
            wrong_observation["egoh_observation"]["evidence"]
        )
        cases.append(("boundary-egoh-identity-invalid", wrong_observation))
        for expected_reason, raw in cases:
            with self.subTest(reason=expected_reason), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                result = _run_boundary_in_directory(copy.deepcopy(raw), root)
                self.assertEqual((result["decision"], result["reason"]), ("held", expected_reason))
                self.assertEqual(list(root.iterdir()), [])
                self.assertIsNone(result["handoff"])
                self.assert_zero_effect_boundary(result)

    def test_nested_invalid_egoh_observation_holds_before_lifecycle_write(self) -> None:
        raw = boundary()
        raw["egoh_observation"]["evidence"]["projection"]["unexpected"] = "raw"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = _run_boundary_in_directory(raw, root)
            self.assertEqual(list(root.iterdir()), [])
        self.assertEqual((result["decision"], result["reason"]), ("held", "boundary-egoh-observation-invalid"))
        self.assertIsNone(result["lifecycle"])
        self.assertIsNone(result["egoh"])
        self.assertIsNone(result["handoff"])
        self.assert_zero_effect_boundary(result)

    def test_public_api_owns_and_cleans_its_ephemeral_directory(self) -> None:
        real_temporary_directory = tempfile.TemporaryDirectory
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            class TemporaryDirectoryInTestRoot:
                def __init__(self, *args, **kwargs) -> None:
                    kwargs["dir"] = root
                    self._owned = real_temporary_directory(*args, **kwargs)

                def __enter__(self) -> str:
                    return self._owned.__enter__()

                def __exit__(self, *args) -> None:
                    self._owned.__exit__(*args)

            with patch.object(operating_core_demo.tempfile, "TemporaryDirectory", TemporaryDirectoryInTestRoot):
                result = operating_core_demo.run_boundary(boundary())
            self.assertEqual(list(root.iterdir()), [])
        self.assertEqual(result["decision"], "review-required")
        self.assert_zero_effect_boundary(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
