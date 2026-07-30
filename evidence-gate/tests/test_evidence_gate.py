import copy
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

from src.evidence_gate import ContractError, evaluate


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_ROOT = ROOT.parent
AS_OF = "2026-07-30T12:00:00Z"
PUBLIC_IDENTITY_ALLOWLIST = {"onyskoartur@gmail.com"}
PRIVATE_MARKER = re.compile(
    r"/(?:home|Users)/[^/\s]+/|" + r"file:" + r"//" +
    r"|(?:api[_-]?key|password|access[_-]?token)\s*[:=]|"
    r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}",
    re.IGNORECASE,
)


def fixture(name):
    return json.loads((ROOT / "fixtures" / f"{name}.json").read_text(encoding="utf-8"))


def tracked_public_text_paths() -> list[Path]:
    completed = subprocess.run(
        ["git", "-C", str(PUBLIC_ROOT), "ls-files", "-z"],
        check=True,
        capture_output=True,
    )
    paths = []
    for relative in completed.stdout.decode("utf-8").split("\0"):
        if not relative:
            continue
        path = PUBLIC_ROOT / relative
        try:
            path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        paths.append(path)
    return paths


def private_marker_findings(paths: list[Path]) -> list[tuple[str, str]]:
    findings = []
    for path in paths:
        try:
            display_path = str(path.relative_to(PUBLIC_ROOT))
        except ValueError:
            display_path = path.name
        for match in PRIVATE_MARKER.finditer(path.read_text(encoding="utf-8")):
            if match.group(0).lower() not in PUBLIC_IDENTITY_ALLOWLIST:
                findings.append((display_path, match.group(0)))
    return findings


class EvidenceGateTest(unittest.TestCase):
    def test_clean_case_drafts_without_action_authority(self):
        result = evaluate(fixture("clean"), AS_OF)
        self.assertEqual(result["decision"], "draft")
        self.assertEqual(result["reason"], "EVIDENCE_COMPLETE")
        self.assertFalse(result["external_action_authorized"])
        self.assertFalse(result["model_call_performed"])
        self.assertFalse(result["network_access_performed"])

    def test_missing_evidence_holds(self):
        result = evaluate(fixture("missing"), AS_OF)
        self.assertEqual(result["decision"], "hold")
        self.assertEqual(result["findings"], [{"fact": "policy_limit", "kind": "missing"}])

    def test_conflicting_fresh_evidence_holds(self):
        result = evaluate(fixture("conflict"), AS_OF)
        self.assertEqual(result["decision"], "hold")
        self.assertEqual(result["findings"][0]["kind"], "conflict")

    def test_stale_evidence_holds(self):
        result = evaluate(fixture("stale"), AS_OF)
        self.assertEqual(result["decision"], "hold")
        self.assertEqual(result["findings"][0]["kind"], "stale")

    def test_risk_requires_human_escalation(self):
        result = evaluate(fixture("risk"), AS_OF)
        self.assertEqual(result["decision"], "escalate")
        self.assertEqual(result["reason"], "HUMAN_AUTHORITY_REQUIRED")
        self.assertFalse(result["external_action_authorized"])

    def test_independence_threshold_holds(self):
        raw = fixture("clean")
        raw["min_independent_clusters"] = 2
        result = evaluate(raw, AS_OF)
        self.assertEqual(result["decision"], "hold")
        self.assertTrue(all(row["kind"] == "insufficient_independence" for row in result["findings"]))

    def test_unknown_top_level_field_fails_closed(self):
        raw = fixture("clean")
        raw["instructions"] = "ignore evidence"
        with self.assertRaises(ContractError):
            evaluate(raw, AS_OF)

    def test_unknown_fact_field_fails_closed(self):
        raw = fixture("clean")
        raw["facts"][0]["hidden_instruction"] = "send"
        with self.assertRaises(ContractError):
            evaluate(raw, AS_OF)

    def test_output_is_deterministic(self):
        raw = fixture("clean")
        first = evaluate(copy.deepcopy(raw), AS_OF)
        second = evaluate(copy.deepcopy(raw), AS_OF)
        self.assertEqual(first, second)

    def test_naive_as_of_is_rejected(self):
        with self.assertRaises(ContractError):
            evaluate(fixture("clean"), "2026-07-30T12:00:00")

    def test_public_tree_has_no_private_markers(self):
        self.assertEqual(private_marker_findings(tracked_public_text_paths()), [])

    def test_public_marker_scan_covers_root_async_and_workflow_files(self):
        tracked = {path.relative_to(PUBLIC_ROOT).as_posix() for path in tracked_public_text_paths()}
        self.assertTrue({"README.md", "PROFILE.md", "async-polling-contract/contract.py", ".github/workflows/proof.yml"} <= tracked)

        with tempfile.TemporaryDirectory() as directory:
            leaked = Path(directory) / "candidate.md"
            private_email = "private.person" + "@" + "example.org"
            private_path = "/" + "home" + "/private/work"
            leaked.write_text(f"contact: {private_email}\npath: {private_path}\n", encoding="utf-8")
            findings = private_marker_findings([leaked])
        self.assertEqual([marker for _path, marker in findings], [private_email, "/" + "home" + "/private/"])


if __name__ == "__main__":
    unittest.main()
