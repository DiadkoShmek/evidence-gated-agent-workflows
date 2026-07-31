from __future__ import annotations

import ast
import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT))

from egoh_demo import (  # noqa: E402
    FORBIDDEN_HANDOFF_KEYS,
    JournalOwner,
    OwnedJournal,
    ValidationError,
    assert_redacted_handoff,
    decide,
    read_journal,
    record_decision,
    run_scenario,
    validate_readonly_observation_target,
    zero_effect_counters,
)
from run_demo import main as run_demo_main  # noqa: E402


NOW = datetime(2026, 7, 31, 12, 1, tzinfo=timezone.utc)


def fixture(name: str) -> Path:
    return ROOT / "fixtures" / f"{name}.json"


def owned_journal(directory: str, relative: str = "journal.jsonl") -> OwnedJournal:
    return JournalOwner(Path(directory)).journal(relative)


class EgoHDemoAcceptanceTests(unittest.TestCase):
    def run_fixture(self, name: str, journal: OwnedJournal) -> dict:
        return run_scenario(fixture(name), journal, now=NOW)

    def test_01_valid_synthetic_evidence_is_non_effecting_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = self.run_fixture("valid-review", owned_journal(temp))
        self.assertEqual(result["decision"]["decision"], "review-required")
        self.assertFalse(result["decision"]["external_action"])
        self.assertEqual(result["decision"]["effect_counters"], zero_effect_counters())
        self.assertIsNotNone(result["handoff"])

    def test_02_missing_or_unexpected_fields_hold_without_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = self.run_fixture("missing-evidence", owned_journal(temp))
        self.assertEqual(result["decision"]["decision"], "held")
        self.assertEqual(result["decision"]["reason"], "scenario-schema-invalid")
        self.assertIsNone(result["handoff"])

    def test_03_altered_evidence_digest_is_held(self) -> None:
        raw = json.loads(fixture("altered-digest").read_text(encoding="utf-8"))
        result = decide(raw, now=NOW)
        self.assertEqual(result["decision"], "held")
        self.assertEqual(result["reason"], "evidence-digest-mismatch")

    def test_04_stale_evidence_is_held(self) -> None:
        raw = json.loads(fixture("stale-evidence").read_text(encoding="utf-8"))
        result = decide(raw, now=NOW)
        self.assertEqual((result["decision"], result["reason"]), ("held", "evidence-stale"))

    def test_05_unknown_tool_is_denied_before_handoff(self) -> None:
        raw = json.loads(fixture("unknown-tool").read_text(encoding="utf-8"))
        result = decide(raw, now=NOW)
        self.assertEqual((result["decision"], result["reason"]), ("held", "tool-denied"))

    def test_06_content_free_contract_rejects_extra_raw_field(self) -> None:
        raw = json.loads(fixture("valid-review").read_text(encoding="utf-8"))
        raw["evidence"]["projection"]["page_text"] = "untrusted content"
        result = decide(raw, now=NOW)
        self.assertEqual((result["decision"], result["reason"]), ("held", "evidence-projection-invalid"))
        self.assertFalse(result["external_action"])

    def test_07_loopback_target_boundary_rejects_wrong_or_ambiguous_input(self) -> None:
        with self.assertRaisesRegex(ValidationError, "cdp-loopback-invalid"):
            validate_readonly_observation_target(
                cdp_list_url="http://192.0.2.1:9222/json/list",
                websocket_url="ws://127.0.0.1:9222/devtools/page/synthetic",
                matching_tab_count=1,
                frame_bytes=1,
            )
        with self.assertRaisesRegex(ValidationError, "target-ambiguous"):
            validate_readonly_observation_target(
                cdp_list_url="http://127.0.0.1:9222/json/list",
                websocket_url="ws://127.0.0.1:9222/devtools/page/synthetic",
                matching_tab_count=2,
                frame_bytes=1,
            )

    def test_08_exact_replay_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            journal = owned_journal(temp)
            first = self.run_fixture("replay", journal)
            second = self.run_fixture("replay", journal)
            rows = read_journal(journal)
        self.assertFalse(first["journal"]["replayed"])
        self.assertTrue(second["journal"]["replayed"])
        self.assertEqual(first["journal"]["event_sha256"], second["journal"]["event_sha256"])
        self.assertEqual(len(rows), 1)

    def test_09_journal_tamper_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            journal = owned_journal(temp)
            self.run_fixture("valid-review", journal)
            event = json.loads(journal.path.read_text(encoding="utf-8"))
            event["reason"] = "tampered"
            journal.path.write_text(json.dumps(event) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValidationError, "journal-digest-invalid"):
                read_journal(journal)

    def test_10_handoff_is_redacted_and_requires_human_action(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = self.run_fixture("replay", owned_journal(temp))
        handoff = result["handoff"]
        self.assertIn("required_human_action", handoff)
        self.assertFalse(handoff["boundary"]["external_action"])
        self.assertTrue(FORBIDDEN_HANDOFF_KEYS.isdisjoint(handoff))
        with self.assertRaisesRegex(ValidationError, "handoff-forbidden-field"):
            assert_redacted_handoff({"outer": {"token": "not-allowed"}})
        for bypass in ("Token", "api-key", "authorization", "cookie", "session", "email"):
            with self.subTest(bypass=bypass), self.assertRaisesRegex(
                ValidationError, "handoff-forbidden-field"
            ):
                assert_redacted_handoff({"outer": {bypass: "not-allowed"}})

    def test_11_effect_counters_and_import_surface_are_zero_and_local(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = self.run_fixture("valid-review", owned_journal(temp))
        self.assertEqual(result["decision"]["effect_counters"], zero_effect_counters())
        source = (ROOT / "egoh_demo.py").read_text(encoding="utf-8")
        imports: set[str] = set()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        self.assertTrue({"socket", "urllib", "requests", "webbrowser", "subprocess"}.isdisjoint(imports))

    def test_12_caller_cannot_supply_or_mint_a_decision(self) -> None:
        raw = json.loads(fixture("valid-review").read_text(encoding="utf-8"))
        raw["expected_decision"] = "handoff-ready"
        result = decide(raw, now=NOW)
        self.assertEqual((result["decision"], result["reason"]), ("held", "scenario-schema-invalid"))
        self.assertFalse(result["external_action"])

    def test_13_no_candidate_is_held_by_derived_policy(self) -> None:
        raw = json.loads(fixture("valid-review").read_text(encoding="utf-8"))
        raw["evidence"]["projection"] = {
            "form_count": 0,
            "field_count": 0,
            "application_form_candidate_present": False,
        }
        raw["evidence_sha256"] = hashlib.sha256(
            json.dumps(
                raw["evidence"], sort_keys=True, separators=(",", ":"), ensure_ascii=True
            ).encode("utf-8")
        ).hexdigest()
        result = decide(raw, now=NOW)
        self.assertEqual(
            (result["decision"], result["reason"]),
            ("held", "application-form-not-observed"),
        )
        self.assertFalse(result["external_action"])

    def test_14_cli_rejects_arbitrary_journal_path(self) -> None:
        original_argv = sys.argv
        try:
            sys.argv = ["run_demo.py", "--journal", "outside.jsonl"]
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as exited:
                    run_demo_main()
        finally:
            sys.argv = original_argv
        self.assertEqual(exited.exception.code, 2)

    def test_15_direct_api_rejects_raw_outside_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            outside = Path(temp) / "outside.jsonl"
            with self.assertRaisesRegex(TypeError, "OwnedJournal"):
                run_scenario(fixture("valid-review"), outside, now=NOW)  # type: ignore[arg-type]
            with self.assertRaisesRegex(TypeError, "OwnedJournal"):
                record_decision(outside, decide(json.loads(fixture("valid-review").read_text()), now=NOW))  # type: ignore[arg-type]
            self.assertFalse(outside.exists())

    def test_16_owned_journal_rejects_symlink_leaf_ancestor_and_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "owned"
            outside = Path(temp) / "outside"
            root.mkdir()
            outside.mkdir()
            owner = JournalOwner(root)
            (root / "leaf.jsonl").symlink_to(outside / "target.jsonl")
            with self.assertRaisesRegex(ValidationError, "journal-path-symlink"):
                owner.journal("leaf.jsonl")
            (root / "linked").symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(ValidationError, "journal-path-symlink"):
                owner.journal("linked/journal.jsonl")
            with self.assertRaisesRegex(ValidationError, "journal-relative-invalid"):
                owner.journal("../outside.jsonl")


if __name__ == "__main__":
    unittest.main()
