from __future__ import annotations

import hashlib
import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PACK = ROOT / "INTEGRATION_RELIABILITY_ACCEPTANCE_PACK.md"
EXPECTED_PACK_SHA256 = "cd1107d793ca7a89cd973c43926cf8533459644a86a90c872d2b9e7cd6fa2cc8"
PUBLICATION_CANDIDATE_PATHS = (
    ROOT / "README.md",
    ROOT / "run_proof.py",
    PACK,
    ROOT / "test_publication_candidate.py",
)
PUBLICATION_CANDIDATE_NAMES = {path.name for path in PUBLICATION_CANDIDATE_PATHS}
PRIVATE_MARKER = re.compile(
    r"/(?:home|Users)/[^/\s]+/|"
    r"file:" + r"//|"
    r"(?:api[_-]?key|password|access[_-]?token)\s*[:=]|"
    r"(?:authorization\s*:\s*|bearer\s+)[A-Za-z0-9._~+/=-]{8,}|"
    r"(?:ghp_|github_pat_|sk-)[A-Za-z0-9_-]{8,}|"
    r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}",
    re.IGNORECASE,
)


class PublicationCandidateTest(unittest.TestCase):
    def test_candidate_manifest_matches_current_worktree_or_clean_ci_checkout(self) -> None:
        completed = subprocess.run(
            ["git", "-C", str(ROOT), "status", "--porcelain=v1", "-z", "--untracked-files=all"],
            check=True,
            capture_output=True,
        )
        records = [record for record in completed.stdout.decode("utf-8").split("\0") if record]
        changed = {record[3:] for record in records}
        self.assertIn(changed, (set(), PUBLICATION_CANDIDATE_NAMES))

    def test_acceptance_pack_is_exact_reviewed_source_and_linked(self) -> None:
        self.assertTrue(PACK.is_file())
        self.assertFalse(PACK.is_symlink())
        payload = PACK.read_bytes()
        self.assertEqual(hashlib.sha256(payload).hexdigest(), EXPECTED_PACK_SHA256)

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(
            "[Integration Reliability Acceptance Pack](INTEGRATION_RELIABILITY_ACCEPTANCE_PACK.md)",
            readme,
        )

    def test_full_publication_candidate_has_no_private_or_credential_markers(self) -> None:
        findings: list[tuple[str, str]] = []
        for path in PUBLICATION_CANDIDATE_PATHS:
            self.assertTrue(path.is_file(), path.name)
            self.assertFalse(path.is_symlink(), path.name)
            for match in PRIVATE_MARKER.finditer(path.read_text(encoding="utf-8")):
                findings.append((path.name, match.group(0)))
        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
