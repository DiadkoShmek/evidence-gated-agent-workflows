from __future__ import annotations

import hashlib
import json
import os
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
CAPABILITY = ROOT / "CAPABILITY_UA.md"
LANDING = ROOT / "docs" / "index.html"
LANDING_STYLE = ROOT / "docs" / "styles.css"
PROOF_EXPERIENCE = ROOT / "docs" / "proof-experience.js"
INQUIRY = ROOT / ".github" / "ISSUE_TEMPLATE" / "client-inquiry.yml"
PAGES_WORKFLOW = ROOT / ".github" / "workflows" / "pages.yml"
EGOH = ROOT / "egoh-demo"
EVIDENCE_GATE = ROOT / "evidence-gate"
TRACE_AS_OF = "2026-07-30T12:00:00Z"
MANIFEST = EGOH / "public-pack" / "PUBLICATION_MANIFEST.json"
EXPECTED_PACK_SHA256 = "cd1107d793ca7a89cd973c43926cf8533459644a86a90c872d2b9e7cd6fa2cc8"
EXPECTED_CAPABILITY_SHA256 = "e8794846a363961398bf1547b5f930d446e41a20c43e105adf3c5443abba1eed"
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


def evaluate_evidence_fixture(name: str) -> dict[str, object]:
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [
            sys.executable,
            str(EVIDENCE_GATE / "src" / "evidence_gate.py"),
            "--input",
            str(EVIDENCE_GATE / "fixtures" / f"{name}.json"),
            "--as-of",
            TRACE_AS_OF,
        ],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    outcome = json.loads(completed.stdout)
    if not isinstance(outcome, dict):
        raise AssertionError("evidence gate output must be an object")
    return outcome


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
        self.assertTrue(CAPABILITY.is_file())
        paths = set(self.tracked_paths())
        paths.add(CAPABILITY)
        paths.add(PROOF_EXPERIENCE)
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

    def test_ukrainian_capability_brief_is_exact_and_linked(self) -> None:
        self.assertTrue(CAPABILITY.is_file())
        self.assertFalse(CAPABILITY.is_symlink())
        self.assertEqual(sha256_file(CAPABILITY), EXPECTED_CAPABILITY_SHA256)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("[Український capability brief](CAPABILITY_UA.md)", readme)

    def test_public_landing_is_static_bounded_and_points_to_exact_owner_routes(self) -> None:
        landing = LANDING.read_text(encoding="utf-8")
        style = LANDING_STYLE.read_text(encoding="utf-8")
        scripts = re.findall(r'<script\s+src="([^"]+)"\s+defer></script>', landing)
        self.assertEqual(scripts, ["proof-experience.js"])
        self.assertEqual(landing.lower().count("<script"), 1)
        self.assertTrue(PROOF_EXPERIENCE.is_file())
        self.assertNotIn("<form", landing.lower())
        self.assertNotIn("http://", landing.lower())
        self.assertNotRegex(landing, r"(?:/home/|\.openclaw|Дзеркало|Комната поля|Omnigen)")
        self.assertEqual(
            set(re.findall(r'https://[^"< ]+', landing)),
            {
                "https://github.com/DiadkoShmek/evidence-gated-agent-workflows",
                "https://github.com/DiadkoShmek/evidence-gated-agent-workflows/issues/new?template=client-inquiry.yml",
            },
        )
        self.assertIn("Fail-Closed Provenance Adapter Sprint", landing)
        self.assertIn("$1,500", landing)
        self.assertIn("does not prove", landing)
        self.assertIn("Illustrative browser-local replay", landing)
        self.assertNotIn("url(", style.lower())
        self.assertNotIn("@import", style.lower())
        resource_urls = re.findall(
            r'<(?:link|script|img|source|iframe|audio|video)\b[^>]*\b(?:href|src|srcset)="([^"]+)"',
            landing,
        )
        self.assertEqual(resource_urls, ["styles.css", "proof-experience.js"])
        self.assertNotRegex(landing.lower(), r'<link\b[^>]*\brel="?preload\b')
        self.assertLess(len(LANDING.read_bytes()), 32 * 1024)
        self.assertLess(len(LANDING_STYLE.read_bytes()), 32 * 1024)

    def test_failure_trace_explorer_replays_only_checked_in_synthetic_outcomes(self) -> None:
        landing = LANDING.read_text(encoding="utf-8")
        experience = PROOF_EXPERIENCE.read_text(encoding="utf-8")
        for scenario in ("clean", "missing", "stale", "conflict", "risk"):
            outcome = evaluate_evidence_fixture(scenario)
            self.assertFalse(outcome["external_action_authorized"])
            trace_pattern = re.compile(
                rf'"id": "{scenario}".*?'
                rf'"outcome": "{outcome["decision"]}".*?'
                rf'"reason": "{outcome["reason"]}".*?'
                rf'"fixtureDecision": "{outcome["decision"]}".*?'
                r'"externalActionAuthorized": false',
                re.DOTALL,
            )
            self.assertRegex(experience, trace_pattern)
            self.assertIn(f'data-trace-scenario="{scenario}"', landing)
        self.assertEqual(experience.count('"externalActionAuthorized": false'), 5)
        self.assertIn("separate checked-in <code>evidence-gate</code> fixtures", landing)
        self.assertIn("current checked-in explorer source contains no network, storage, or telemetry APIs", landing)
        self.assertIn("not Python equivalence, EGOH parity, production safety, certification, client validity, or external authorization", landing)

    def test_failure_trace_initial_dom_matches_canonical_clean_fixture(self) -> None:
        landing = LANDING.read_text(encoding="utf-8")
        clean = evaluate_evidence_fixture("clean")
        expected = {
            "outcome": clean["decision"],
            "reason": clean["reason"],
            "decision": clean["decision"],
            "authorized": canonical_json(clean["external_action_authorized"]),
        }
        actual: dict[str, str] = {}
        for field in expected:
            match = re.search(rf"data-trace-{field}>([^<]+)</dd>", landing)
            self.assertIsNotNone(match, field)
            actual[field] = match.group(1)  # type: ignore[union-attr]
        self.assertEqual(actual, expected)
        selected = re.findall(
            r'<button[^>]+data-trace-scenario="([^"]+)"[^>]+aria-pressed="true"',
            landing,
        )
        self.assertEqual(selected, ["clean"])

    def test_failure_trace_explorer_has_no_input_or_external_runtime_surface(self) -> None:
        landing = LANDING.read_text(encoding="utf-8").lower()
        experience = PROOF_EXPERIENCE.read_text(encoding="utf-8").lower()
        self.assertNotRegex(landing, r"<(?:form|input|select|textarea)\b")
        self.assertNotIn("contenteditable", landing)
        for forbidden in (
            "fetch(", "xmlhttprequest", "sendbeacon", "localstorage", "sessionstorage",
            "indexeddb", "document.cookie", "window.open", "websocket", "eventsource",
            "<script", "http://", "https://",
        ):
            self.assertNotIn(forbidden, experience)
        self.assertNotRegex(experience, r"(?:prompt|confirm|alert)\s*\(")

    def test_public_inquiry_warns_without_claiming_enforced_sanitization(self) -> None:
        inquiry = INQUIRY.read_text(encoding="utf-8")
        self.assertIn("This is a public issue", inquiry)
        for forbidden in ("email", "phone", "password", "token", "api key", "upload"):
            self.assertNotRegex(inquiry.lower(), rf"id:\s*{re.escape(forbidden)}")
        for required in ("id: workflow", "id: failure", "id: proof", "id: boundary"):
            self.assertIn(required, inquiry)
        self.assertIn("production activation", inquiry)
        self.assertIn("private code", inquiry)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("sanitized workflow inquiry", readme)

    def test_pages_deploys_only_sealed_static_directory(self) -> None:
        workflow = PAGES_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("needs: verify", workflow)
        self.assertIn("run: python3 run_proof.py", workflow)
        self.assertIn("path: docs", workflow)
        self.assertIn("contents: read", workflow)
        self.assertIn("pages: write", workflow)
        self.assertIn("id-token: write", workflow)
        self.assertNotIn("pull_request", workflow)
        self.assertNotRegex(workflow, r"uses:\s+actions/[^\s]+@v\d")

    def test_one_command_proof_pins_valid_fixture_epoch_and_expected_decision(self) -> None:
        runner = (ROOT / "run_proof.py").read_text(encoding="utf-8")
        self.assertIn('"2026-07-31T12:01:00+00:00"', runner)
        self.assertIn('"--expect-decision"', runner)
        self.assertIn('"review-required"', runner)
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        completed = subprocess.run(
            [
                sys.executable,
                str(EGOH / "run_demo.py"),
                "--scenario",
                "valid-review",
                "--as-of",
                "2026-07-31T12:01:00+00:00",
                "--expect-decision",
                "review-required",
            ],
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )
        result = json.loads(completed.stdout)
        self.assertEqual(result["decision"]["decision"], "review-required")
        self.assertIsNotNone(result["handoff"])

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
