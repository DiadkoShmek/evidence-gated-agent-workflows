from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
PACK = ROOT / "INTEGRATION_RELIABILITY_ACCEPTANCE_PACK.md"
EGOH = ROOT / "egoh-demo"
MANIFEST = EGOH / "public-pack" / "PUBLICATION_MANIFEST.json"
EXPECTED_PACK_SHA256 = "cd1107d793ca7a89cd973c43926cf8533459644a86a90c872d2b9e7cd6fa2cc8"
MANIFEST_SCHEMA = "evidence-gated-public-candidate-manifest-v1"
MANIFEST_EXCLUSIONS = [
    ".git/**",
    ".pytest_cache/**",
    "**/__pycache__/**",
    "**/*.pyc",
    "**/*.pyo",
    "egoh-demo/public-pack/PUBLICATION_MANIFEST.json",
]
PRIVATE_MARKER = re.compile(
    r"/(?:home|Users)/[^/\s]+/|"
    r"file:" + r"//|"
    r"(?:api[_-]?key|password|access[_-]?token)\s*[:=]|"
    r"(?:authorization\s*:\s*|bearer\s+)[A-Za-z0-9._~+/=-]{8,}|"
    r"(?:ghp_|github_pat_|sk-)[A-Za-z0-9_-]{8,}|"
    r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}",
    re.IGNORECASE,
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


class PublicationCandidateTest(unittest.TestCase):
    def is_cache_path(self, path: Path) -> bool:
        return path.name == "__pycache__" or path.suffix in {".pyc", ".pyo"}

    def tracked_paths(self) -> list[Path]:
        completed = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "-z"], check=True, capture_output=True
        )
        paths = [ROOT / item for item in completed.stdout.decode("utf-8").split("\0") if item]
        for path in paths:
            self.assertTrue(path.is_file(), path)
            self.assertFalse(path.is_symlink(), path)
        return paths

    def content_paths(self) -> list[Path]:
        self.assertTrue(EGOH.is_dir())
        paths = set(self.tracked_paths())
        paths.update(path for path in EGOH.rglob("*") if path.is_file())
        return sorted(
            path for path in paths if path != MANIFEST and not self.is_cache_path(path)
        )

    def all_candidate_paths(self) -> list[Path]:
        return sorted([*self.content_paths(), MANIFEST])

    def expected_manifest_entries(self) -> list[dict[str, str]]:
        return [
            {"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path)}
            for path in self.content_paths()
        ]

    def read_manifest(self) -> dict[str, object]:
        self.assertTrue(MANIFEST.is_file())
        self.assertFalse(MANIFEST.is_symlink())
        payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(set(payload), {"schema", "algorithm", "exclusions", "files", "tree_sha256"})
        self.assertEqual(payload["schema"], MANIFEST_SCHEMA)
        self.assertEqual(payload["algorithm"], "sha256")
        self.assertEqual(payload["exclusions"], MANIFEST_EXCLUSIONS)
        self.assertIsInstance(payload["files"], list)
        self.assertIsInstance(payload["tree_sha256"], str)
        return payload

    def test_candidate_manifest_matches_current_worktree_or_clean_ci_checkout(self) -> None:
        completed = subprocess.run(
            ["git", "-C", str(ROOT), "status", "--porcelain=v1", "-z", "--untracked-files=all"],
            check=True,
            capture_output=True,
        )
        records = [record for record in completed.stdout.decode("utf-8").split("\0") if record]
        changed = {record[3:] for record in records}
        allowed = {str(path.relative_to(ROOT)) for path in self.all_candidate_paths()}
        self.assertTrue(changed <= allowed)

    def test_publication_manifest_binds_every_public_candidate_file(self) -> None:
        manifest = self.read_manifest()
        expected = self.expected_manifest_entries()
        self.assertEqual(manifest["files"], expected)
        self.assertEqual(
            manifest["tree_sha256"],
            hashlib.sha256(canonical_json(expected).encode("utf-8")).hexdigest(),
        )
        committed = {str(path.relative_to(ROOT)) for path in self.tracked_paths() if path != MANIFEST}
        manifest_paths = {entry["path"] for entry in expected}
        self.assertTrue(committed <= manifest_paths)

    def test_acceptance_pack_is_exact_reviewed_source_and_linked(self) -> None:
        self.assertTrue(PACK.is_file())
        self.assertFalse(PACK.is_symlink())
        self.assertEqual(sha256_file(PACK), EXPECTED_PACK_SHA256)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(
            "[Integration Reliability Acceptance Pack](INTEGRATION_RELIABILITY_ACCEPTANCE_PACK.md)",
            readme,
        )

    def test_public_pack_examples_are_current_and_bound_to_valid_review(self) -> None:
        sys.path.insert(0, str(EGOH))
        try:
            from egoh_demo import JournalOwner, assert_redacted_handoff, read_journal, run_scenario
        finally:
            sys.path.pop(0)
        with tempfile.TemporaryDirectory(prefix="egoh-public-pack-test-") as directory:
            journal = JournalOwner(Path(directory)).journal()
            result = run_scenario(
                EGOH / "fixtures" / "valid-review.json",
                journal,
                now=datetime(2026, 7, 31, 12, 1, tzinfo=timezone.utc),
            )
            generated_journal = read_journal(journal)
        handoff_path = EGOH / "public-pack" / "example-valid-review.handoff.json"
        checked_in_handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
        self.assertEqual(checked_in_handoff, result["handoff"])
        assert_redacted_handoff(checked_in_handoff)
        checked_in_journal = [
            json.loads(line)
            for line in (EGOH / "public-pack" / "example-valid-review.journal.jsonl").read_text(
                encoding="utf-8"
            ).splitlines()
        ]
        self.assertEqual(checked_in_journal, generated_journal)
        test_names = re.findall(
            r"^    def (test_\d+_[a-z0-9_]+)\(",
            (EGOH / "tests" / "test_egoh_demo.py").read_text(encoding="utf-8"),
            re.MULTILINE,
        )
        results = (EGOH / "public-pack" / "TEST_RESULTS.md").read_text(encoding="utf-8")
        self.assertIn(f"Ran {len(test_names)} tests", results)
        for name in test_names:
            self.assertIn(f"{name} ... ok", results)

    def test_full_publication_candidate_has_no_private_or_credential_markers(self) -> None:
        findings: list[tuple[str, str]] = []
        for path in self.all_candidate_paths():
            self.assertTrue(path.is_file(), path.name)
            self.assertFalse(path.is_symlink(), path.name)
            for match in PRIVATE_MARKER.finditer(path.read_text(encoding="utf-8")):
                findings.append((str(path.relative_to(ROOT)), match.group(0)))
        self.assertEqual(findings, [])

    def test_egoh_candidate_contains_no_caches(self) -> None:
        cache_paths = [
            path.relative_to(ROOT)
            for path in EGOH.rglob("*")
            if self.is_cache_path(path)
        ]
        self.assertEqual(cache_paths, [])


if __name__ == "__main__":
    unittest.main()
