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

from generate_publication_manifest import (
    MANIFEST_EXCLUSIONS,
    content_paths as canonical_content_paths,
    is_excluded,
    manifest_payload,
)


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
PACK = ROOT / "INTEGRATION_RELIABILITY_ACCEPTANCE_PACK.md"
CAPABILITY = ROOT / "CAPABILITY_UA.md"
LANDING = ROOT / "docs" / "index.html"
LANDING_EN = ROOT / "docs" / "en.html"
CASE_STUDY = ROOT / "docs" / "case-study.html"
ARCHITECTURE = ROOT / "docs" / "architecture.html"
AI_SYSTEMS_SPRINT = ROOT / "docs" / "ai-systems-sprint.html"
ROBOTS = ROOT / "docs" / "robots.txt"
SITEMAP = ROOT / "docs" / "sitemap.xml"
LANDING_STYLE = ROOT / "docs" / "styles.css"
PROOF_EXPERIENCE = ROOT / "docs" / "proof-experience.js"
INTAKE_EXPERIENCE = ROOT / "docs" / "intake-experience.js"
OPERATING_CORE_EXPERIENCE = ROOT / "docs" / "operating-core-experience.js"
OPERATING_CORE = ROOT / "operating-core-demo"
MANIFEST_GENERATOR = ROOT / "generate_publication_manifest.py"
INQUIRY = ROOT / ".github" / "ISSUE_TEMPLATE" / "client-inquiry.yml"
PAGES_WORKFLOW = ROOT / ".github" / "workflows" / "pages.yml"
PROOF_WORKFLOW = ROOT / ".github" / "workflows" / "proof.yml"
EGOH = ROOT / "egoh-demo"
EVIDENCE_GATE = ROOT / "evidence-gate"
TRACE_AS_OF = "2026-07-30T12:00:00Z"
MANIFEST = EGOH / "public-pack" / "PUBLICATION_MANIFEST.json"
EXPECTED_PACK_SHA256 = "cd1107d793ca7a89cd973c43926cf8533459644a86a90c872d2b9e7cd6fa2cc8"
EXPECTED_CAPABILITY_SHA256 = "cd4267f8aaa5a6e4137cd181de6199c009874adef77c9402d7be00be6b9f73b3"
MANIFEST_SCHEMA = "evidence-gated-public-candidate-manifest-v1"
PRIVATE_MARKER = re.compile(
    r"/(?:home|Users)/[^/\s]+/|"
    r"file:" + r"//|"
    r"(?:api[_-]?key|password|access[_-]?token)\s*[:=]|"
    r"(?:authorization\s*:\s*|bearer\s+)[A-Za-z0-9._~+/=-]{8,}|"
    r"(?:ghp_|github_pat_|sk-)[A-Za-z0-9_-]{8,}|"
    r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}",
    re.IGNORECASE,
)
PUBLIC_CONTACT_EMAIL = "onyskoartur" + chr(64) + "gmail.com"
PUBLIC_CONTACT_PATHS = {"docs/ai-systems-sprint.html", "docs/architecture.html", "docs/case-study.html", "docs/en.html", "docs/index.html"}


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


def replay_failure_trace_explorer_dom(language: str) -> dict[str, object]:
    """Run the checked-in explorer against a deliberately minimal DOM contract."""
    harness = r'''
const fs = require("fs");
const vm = require("vm");

const fieldSelectors = [
  "[data-trace-title]",
  "[data-trace-outcome]",
  "[data-trace-reason]",
  "[data-trace-decision]",
  "[data-trace-authorized]",
  "[data-trace-explanation]",
];
const fields = Object.fromEntries(
  fieldSelectors.map((selector) => [selector, { textContent: "" }]),
);
const controls = ["clean", "missing", "stale", "conflict", "risk"].map((id) => {
  const control = {
    dataset: { traceScenario: id },
    attributes: {},
    handlers: {},
    selected: false,
    classList: {
      toggle(name, selected) {
        if (name !== "is-selected") throw new Error(`unexpected class ${name}`);
        control.selected = Boolean(selected);
      },
    },
    setAttribute(name, value) {
      control.attributes[name] = String(value);
    },
    addEventListener(name, handler) {
      if (name !== "click" || control.handlers.click) {
        throw new Error(`unexpected listener ${name}`);
      }
      control.handlers.click = handler;
    },
  };
  return control;
});
const document = {
  documentElement: { lang: process.argv.at(-2) },
  querySelectorAll(selector) {
    if (selector !== "[data-trace-scenario]") throw new Error(`unexpected query ${selector}`);
    return controls;
  },
  querySelector(selector) {
    if (!(selector in fields)) throw new Error(`unexpected query ${selector}`);
    return fields[selector];
  },
};
function snapshot() {
  return {
    title: fields["[data-trace-title]"].textContent,
    outcome: fields["[data-trace-outcome]"].textContent,
    reason: fields["[data-trace-reason]"].textContent,
    decision: fields["[data-trace-decision]"].textContent,
    authorized: fields["[data-trace-authorized]"].textContent,
    explanation: fields["[data-trace-explanation]"].textContent,
    controls: controls.map((control) => ({
      id: control.dataset.traceScenario,
      classSelected: control.selected,
      ariaPressed: control.attributes["aria-pressed"],
    })),
  };
}

const sourcePath = process.argv.at(-1);
vm.runInNewContext(fs.readFileSync(sourcePath, "utf8"), { document, Map, Object, String }, {
  filename: sourcePath,
});
const initial = snapshot();
const risk = controls.find((control) => control.dataset.traceScenario === "risk");
if (!risk || typeof risk.handlers.click !== "function") throw new Error("missing risk click handler");
risk.handlers.click();
console.log(JSON.stringify({ initial, risk: snapshot() }));
'''
    completed = subprocess.run(
        ["node", "-e", harness, language, str(PROOF_EXPERIENCE)],
        check=True,
        capture_output=True,
        text=True,
    )
    outcome = json.loads(completed.stdout)
    if not isinstance(outcome, dict):
        raise AssertionError("failure trace runtime output must be an object")
    return outcome


def replay_acceptance_packet_builder_dom() -> dict[str, object]:
    """Run the local packet builder with only its declared DOM surface."""
    harness = r'''
const fs = require("fs");
const vm = require("vm");

const options = [
  ["workflow", "agent-result-to-internal-tool"],
  ["workflow", "model-artifact-to-runtime"],
  ["workflow", "async-job-status"],
  ["workflow", "data-receipt"],
  ["source", "buyer-declared-sanitized-sample-artifact"],
  ["source", "source-interface-description-only"],
  ["target", "one-internal-review-boundary"],
  ["target", "one-bounded-runtime-adapter"],
  ["decision_owner_role", "human-review-owner-to-be-named"],
  ["decision_owner_role", "team-operator-to-be-named"],
  ["costly_failure", "missing-evidence"],
  ["costly_failure", "stale-evidence"],
  ["costly_failure", "malformed-artifact"],
  ["costly_failure", "contradictory-evidence"],
  ["five_day_evidence", "valid-fixture-plus-hostile-fail-closed"],
  ["five_day_evidence", "bounded-polling-terminal-state"],
  ["five_day_evidence", "decision-trace-known-limits"],
  ["test_environment", "sanitized-example-only"],
  ["test_environment", "sanitized-test-environment"],
  ["test_environment", "discovery-before-artifact"],
  ["human_action_boundary", "human-approval-required-before-any-next-action"],
  ["human_action_boundary", "manual-review-only"],
  ["boundary_declaration", "buyer-declares-public-summary-only"],
];
const controls = options.map(([field, value]) => {
  const control = {
    dataset: { intakeField: field, intakeValue: value },
    attributes: {},
    handlers: {},
    selected: false,
    classList: {
      toggle(name, selected) {
        if (name !== "is-selected") throw new Error(`unexpected class ${name}`);
        control.selected = Boolean(selected);
      },
    },
    setAttribute(name, value) {
      control.attributes[name] = String(value);
    },
    addEventListener(name, handler) {
      if (name !== "click" || control.handlers.click) {
        throw new Error(`unexpected listener ${name}`);
      }
      control.handlers.click = handler;
    },
  };
  return control;
});
const packet = { textContent: "" };
const bridge = { textContent: "" };
const reset = { handlers: {}, addEventListener(name, handler) {
  if (name !== "click" || reset.handlers.click) throw new Error(`unexpected listener ${name}`);
  reset.handlers.click = handler;
} };
const document = {
  querySelectorAll(selector) {
    if (selector !== "[data-intake-field]") throw new Error(`unexpected query ${selector}`);
    return controls;
  },
  querySelector(selector) {
    if (selector === "[data-intake-packet]") return packet;
    if (selector === "[data-issue-form-bridge]") return bridge;
    if (selector === "[data-intake-reset]") return reset;
    throw new Error(`unexpected query ${selector}`);
  },
};
function snapshot() {
  return {
    packet: JSON.parse(packet.textContent),
    bridge: JSON.parse(bridge.textContent),
    controls: controls.map((control) => ({
      field: control.dataset.intakeField,
      value: control.dataset.intakeValue,
      classSelected: control.selected,
      ariaPressed: control.attributes["aria-pressed"],
    })),
  };
}

const sourcePath = process.argv.at(-1);
function forbiddenCapability(name) {
  const fail = () => { throw new Error(`forbidden capability used: ${name}`); };
  return new Proxy(fail, { get: fail, set: fail, apply: fail, construct: fail });
}
vm.runInNewContext(fs.readFileSync(sourcePath, "utf8"), {
  document, Array, Object, String, JSON,
  fetch: forbiddenCapability("fetch"),
  XMLHttpRequest: forbiddenCapability("XMLHttpRequest"),
  WebSocket: forbiddenCapability("WebSocket"),
  EventSource: forbiddenCapability("EventSource"),
  navigator: forbiddenCapability("navigator"),
  window: forbiddenCapability("window"),
  location: forbiddenCapability("location"),
  history: forbiddenCapability("history"),
  localStorage: forbiddenCapability("localStorage"),
  sessionStorage: forbiddenCapability("sessionStorage"),
  indexedDB: forbiddenCapability("indexedDB"),
  caches: forbiddenCapability("caches"),
}, {
  filename: sourcePath,
});
const initial = snapshot();
const changed = controls.find((control) => control.dataset.intakeValue === "contradictory-evidence");
if (!changed || typeof changed.handlers.click !== "function") {
  throw new Error("missing contradictory-evidence click handler");
}
changed.handlers.click();
const partial = snapshot();
const fields = [...new Set(options.map(([field]) => field))];
for (const field of fields) {
  const control = controls.find((candidate) => candidate.dataset.intakeField === field);
  if (!control || typeof control.handlers.click !== "function") {
    throw new Error(`missing ${field} click handler`);
  }
  control.handlers.click();
}
const complete = snapshot();
if (typeof reset.handlers.click !== "function") throw new Error("missing reset click handler");
reset.handlers.click();
console.log(JSON.stringify({ initial, partial, complete, reset: snapshot() }));
'''
    completed = subprocess.run(
        ["node", "-e", harness, str(INTAKE_EXPERIENCE)],
        check=True,
        capture_output=True,
        text=True,
    )
    outcome = json.loads(completed.stdout)
    if not isinstance(outcome, dict):
        raise AssertionError("acceptance packet runtime output must be an object")
    return outcome


def replay_operating_core_map_dom(language: str) -> dict[str, object]:
    """Run the local control-surface map against its declared minimal DOM."""
    harness = r'''
const fs = require("fs");
const vm = require("vm");

const fieldSelectors = [
  "[data-core-stage-id]", "[data-core-title]", "[data-core-reference]",
  "[data-core-buyer]", "[data-core-limit]", "[data-core-authority]",
  "[data-core-external]", "[data-core-production]", "[data-core-provider]",
];
const fields = Object.fromEntries(fieldSelectors.map((selector) => [selector, { textContent: "" }]));
const controls = [
  "system-boundary", "evidence-decision", "bounded-lifecycle", "human-authority", "receipt-handoff",
].map((id) => {
  const control = {
    dataset: { coreStage: id }, attributes: {}, handlers: {}, selected: false,
    classList: { toggle(name, selected) {
      if (name !== "is-selected") throw new Error(`unexpected class ${name}`);
      control.selected = Boolean(selected);
    } },
    setAttribute(name, value) { control.attributes[name] = String(value); },
    addEventListener(name, handler) {
      if (name !== "click" || control.handlers.click) throw new Error(`unexpected listener ${name}`);
      control.handlers.click = handler;
    },
  };
  return control;
});
const document = {
  documentElement: { lang: process.argv.at(-2) },
  querySelectorAll(selector) {
    if (selector !== "[data-core-stage]") throw new Error(`unexpected query ${selector}`);
    return controls;
  },
  querySelector(selector) {
    if (!(selector in fields)) throw new Error(`unexpected query ${selector}`);
    return fields[selector];
  },
};
function snapshot() {
  return {
    stage: fields["[data-core-stage-id]"].textContent,
    title: fields["[data-core-title]"].textContent,
    reference: fields["[data-core-reference]"].textContent,
    buyer: fields["[data-core-buyer]"].textContent,
    limit: fields["[data-core-limit]"].textContent,
    authority: fields["[data-core-authority]"].textContent,
    external: fields["[data-core-external]"].textContent,
    production: fields["[data-core-production]"].textContent,
    provider: fields["[data-core-provider]"].textContent,
    controls: controls.map((control) => ({
      id: control.dataset.coreStage, classSelected: control.selected,
      ariaPressed: control.attributes["aria-pressed"],
    })),
  };
}
function forbiddenCapability(name) {
  const fail = () => { throw new Error(`forbidden capability used: ${name}`); };
  return new Proxy(fail, { get: fail, set: fail, apply: fail, construct: fail });
}
const sourcePath = process.argv.at(-1);
vm.runInNewContext(fs.readFileSync(sourcePath, "utf8"), {
  document, Array, Map, Object, String,
  fetch: forbiddenCapability("fetch"), XMLHttpRequest: forbiddenCapability("XMLHttpRequest"),
  WebSocket: forbiddenCapability("WebSocket"), EventSource: forbiddenCapability("EventSource"),
  navigator: forbiddenCapability("navigator"), window: forbiddenCapability("window"),
  location: forbiddenCapability("location"), history: forbiddenCapability("history"),
  localStorage: forbiddenCapability("localStorage"), sessionStorage: forbiddenCapability("sessionStorage"),
  indexedDB: forbiddenCapability("indexedDB"), caches: forbiddenCapability("caches"),
}, { filename: sourcePath });
const initial = snapshot();
const stages = {};
for (const control of controls) {
  if (typeof control.handlers.click !== "function") {
    throw new Error(`missing ${control.dataset.coreStage} click handler`);
  }
  control.handlers.click();
  stages[control.dataset.coreStage] = snapshot();
}
console.log(JSON.stringify({ initial, stages }));
'''
    completed = subprocess.run(
        ["node", "-e", harness, language, str(OPERATING_CORE_EXPERIENCE)],
        check=True,
        capture_output=True,
        text=True,
    )
    outcome = json.loads(completed.stdout)
    if not isinstance(outcome, dict):
        raise AssertionError("operating core runtime output must be an object")
    return outcome


class PublicationCandidateTest(unittest.TestCase):
    def test_technical_case_study_is_indexable_bounded_and_linked(self) -> None:
        case_study = CASE_STUDY.read_text(encoding="utf-8")
        english = LANDING_EN.read_text(encoding="utf-8")
        ukrainian = LANDING.read_text(encoding="utf-8")
        robots = ROBOTS.read_text(encoding="utf-8")
        sitemap = SITEMAP.read_text(encoding="utf-8")

        self.assertIn('<link rel="canonical" href="https://diadkoshmek.github.io/evidence-gated-agent-workflows/case-study.html">', case_study)
        self.assertIn('"@type":"TechArticle"', case_study)
        self.assertIn("python3 run_proof.py", case_study)
        self.assertIn("External action authorized</dt><dd>false", case_study)
        self.assertIn("does not establish production safety", case_study)
        self.assertIn('href="case-study.html"', english)
        self.assertIn('href="case-study.html"', ukrainian)
        self.assertEqual(
            robots,
            "User-agent: *\nAllow: /\n\nSitemap: https://diadkoshmek.github.io/evidence-gated-agent-workflows/sitemap.xml\n",
        )
        self.assertEqual(
            sitemap.count("<url>"),
            5,
        )
        self.assertIn("https://diadkoshmek.github.io/evidence-gated-agent-workflows/case-study.html", sitemap)
        for forbidden in ("fetch(", "XMLHttpRequest", "localStorage", "sessionStorage", "navigator.sendBeacon"):
            self.assertNotIn(forbidden, case_study)

    def test_architecture_note_is_runnable_bounded_and_linked(self) -> None:
        architecture = ARCHITECTURE.read_text(encoding="utf-8")
        english = LANDING_EN.read_text(encoding="utf-8")
        sitemap = SITEMAP.read_text(encoding="utf-8")

        self.assertIn('<link rel="canonical" href="https://diadkoshmek.github.io/evidence-gated-agent-workflows/architecture.html">', architecture)
        self.assertIn('"@type":"TechArticle"', architecture)
        self.assertIn("python3 run_proof.py", architecture)
        self.assertIn("external_action_authorized = false", architecture)
        self.assertIn("the synthetic polling reference does not claim it", architecture)
        self.assertIn("complete work still requires a separately accepted EGOH observation", architecture)
        self.assertIn("six small owners", architecture)
        self.assertNotIn("five small owners", architecture)
        self.assertIn("Immutable artifact handoff", architecture)
        self.assertIn("historical byte family", architecture)
        self.assertIn("Agent action admission", architecture)
        self.assertIn("typed pre-effect commitment before deterministic local simulation", architecture)
        self.assertIn("receipt-last descriptor-pinned artifact handoff", architecture)
        self.assertIn("symlinks, and replaced filesystem generations", architecture)
        self.assertIn("case and fact identities, evidence hashes, freshness, conflicts", architecture)
        self.assertNotIn("A client adapter can extend this", architecture)
        self.assertNotIn("source generation, and authority are checked", architecture)
        self.assertIn("does not establish production safety", architecture)
        self.assertIn('href="architecture.html"', english)
        self.assertIn('href="architecture.html"', LANDING.read_text(encoding="utf-8"))
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("architecture of the evidence-gated boundary", readme)
        self.assertIn("six checked owners", readme)
        self.assertNotIn("five checked owners", readme)
        self.assertNotIn("four checked owners", readme)
        self.assertIn("receipt-last immutable artifact publication", readme)
        self.assertIn("Immutable artifact handoff", readme)
        self.assertIn("Agent action admission", readme)
        self.assertNotIn("it is not claimed by the synthetic demo", readme)
        self.assertIn("https://diadkoshmek.github.io/evidence-gated-agent-workflows/architecture.html", sitemap)
        for forbidden in ("fetch(", "XMLHttpRequest", "localStorage", "sessionStorage", "navigator.sendBeacon"):
            self.assertNotIn(forbidden, architecture)

    def test_ai_systems_sprint_is_specific_bounded_and_linked(self) -> None:
        page = AI_SYSTEMS_SPRINT.read_text(encoding="utf-8")
        english = LANDING_EN.read_text(encoding="utf-8")
        ukrainian = LANDING.read_text(encoding="utf-8")
        architecture = ARCHITECTURE.read_text(encoding="utf-8")
        case_study = CASE_STUDY.read_text(encoding="utf-8")
        sitemap = SITEMAP.read_text(encoding="utf-8")

        self.assertIn('<link rel="canonical" href="https://diadkoshmek.github.io/evidence-gated-agent-workflows/ai-systems-sprint.html">', page)
        self.assertIn('"@type":"Service"', page)
        self.assertIn('"price":"1500"', page)
        self.assertIn("Not a platform subscription or a migration.", page)
        self.assertIn("AI Systems Proof Sprint — $1,500 fixed", page)
        self.assertIn("Release Integrity Pack — $4,500 fixed", page)
        self.assertIn("agent action admission demo", page)
        self.assertIn("It grants no real tool or effect authority.", page)
        self.assertIn("only as a separately scoped follow-on after a completed Proof Sprint", page)
        self.assertNotIn("$7,500", page)
        for seam in (
            "Memory or retrieval → next-agent context",
            "Dataset or evaluation → release decision",
            "Tool or model result → external effect",
            "Workflow or sandbox state → later continuation",
        ):
            self.assertIn(seam, page)
        for deliverable in ("Boundary contract", "Bounded adapter", "Hostile proof", "Decision receipt", "Engineering handoff"):
            self.assertIn(deliverable, page)
        self.assertIn("external authority  → false unless separately granted", page)
        self.assertIn("does not claim production safety", page)
        self.assertIn("sanitized summary only", page)
        self.assertIn(
            '<a class="button secondary" href="https://github.com/DiadkoShmek/evidence-gated-agent-workflows">Run the public proof</a>',
            page,
        )
        self.assertIn(
            '<a class="button secondary" href="https://github.com/DiadkoShmek/evidence-gated-agent-workflows/releases/tag/public-proof-v1.7.0">Download immutable public proof v1.7</a>',
            page,
        )
        self.assertIn(
            "The repository link follows source changes; v1.7 is the immutable release snapshot with its published checksum.",
            page,
        )
        issue_url = "https://github.com/DiadkoShmek/evidence-gated-agent-workflows/issues/new?template=client-inquiry.yml"
        hero = re.search(r'<header class="article-hero shell">.*?</header>', page, re.DOTALL)
        self.assertIsNotNone(hero)
        hero_markup = hero.group(0)  # type: ignore[union-attr]
        self.assertEqual(hero_markup.count(issue_url), 1)
        self.assertIn(">Use the review-only issue form</a>", hero_markup)
        self.assertIn('href="en.html#intake">Build a local review draft</a>', hero_markup)
        self.assertEqual(page.count(issue_url), 2)
        self.assertEqual(page.count('href="en.html#intake"'), 2)
        self.assertEqual(page.count('>Build a local review draft</a>'), 2)
        intake = re.search(r'<section id="intake".*?</section>', english, re.DOTALL)
        self.assertIsNotNone(intake)
        self.assertIn("browser-local planning draft", intake.group(0))  # type: ignore[union-attr]
        self.assertIn('"automatic_submit": false', intake.group(0))  # type: ignore[union-attr]
        self.assertIn("Manually open the existing English public GitHub Issue Form", intake.group(0))  # type: ignore[union-attr]
        self.assertIn('href="ai-systems-sprint.html"', english)
        self.assertIn('href="ai-systems-sprint.html"', ukrainian)
        self.assertIn('href="ai-systems-sprint.html"', architecture)
        self.assertIn("https://diadkoshmek.github.io/evidence-gated-agent-workflows/ai-systems-sprint.html", sitemap)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("**AI Systems Proof Sprint**: one fail-closed provenance", readme)
        self.assertIn("fixed first-step price is **$1,500**.", readme)
        self.assertIn("one bounded fail-closed provenance adapter", readme)
        self.assertIn(
            "https://diadkoshmek.github.io/evidence-gated-agent-workflows/ai-systems-sprint.html",
            readme,
        )
        self.assertNotIn("I offer a fixed-scope **Fail-Closed Provenance Adapter Sprint**", readme)
        for public_cta in (architecture, case_study):
            self.assertIn("<strong>AI Systems Proof Sprint</strong>", public_cta)
            self.assertIn("One fail-closed provenance adapter for a sanitized source-to-target handoff", public_cta)
            self.assertNotIn("Fail-Closed Provenance Adapter Sprint", public_cta)
        for forbidden in ("fetch(", "XMLHttpRequest", "localStorage", "sessionStorage", "navigator.sendBeacon"):
            self.assertNotIn(forbidden, page)

    def test_exact_public_contact_is_private_first_and_strictly_allowlisted(self) -> None:
        expected_href = f"mailto:{PUBLIC_CONTACT_EMAIL}?subject=One%20broken%20AI%20handoff"
        for path in (AI_SYSTEMS_SPRINT, ARCHITECTURE, CASE_STUDY, LANDING_EN, LANDING):
            content = path.read_text(encoding="utf-8")
            self.assertIn(expected_href, content)
            self.assertIn("sanitized summary", content)
            self.assertIn("issues/new?template=client-inquiry.yml", content)

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
        self.assertTrue(OPERATING_CORE.is_dir())
        self.assertTrue(MANIFEST_GENERATOR.is_file())
        return canonical_content_paths(ROOT)

    def all_candidate_paths(self) -> list[Path]:
        return sorted([*self.content_paths(), MANIFEST])

    def expected_manifest_entries(self) -> list[dict[str, str]]:
        return manifest_payload(ROOT)["files"]  # type: ignore[return-value]

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
        expected_payload = manifest_payload(ROOT)
        expected = self.expected_manifest_entries()
        self.assertEqual(manifest, expected_payload)
        committed = {str(path.relative_to(ROOT)) for path in self.tracked_paths() if path != MANIFEST}
        manifest_paths = {entry["path"] for entry in expected}
        self.assertTrue(committed <= manifest_paths)

    def test_publication_manifest_check_uses_the_canonical_generator(self) -> None:
        subprocess.run([sys.executable, str(MANIFEST_GENERATOR), "--check"], cwd=ROOT, check=True)

    def test_manifest_exclusion_predicate_rejects_nested_cache_without_manifest_drift(self) -> None:
        baseline = manifest_payload(ROOT)
        with tempfile.TemporaryDirectory(dir=OPERATING_CORE) as directory:
            cached = Path(directory) / "nested" / ".pytest_cache" / "generated.pyc"
            cached.parent.mkdir(parents=True)
            cached.write_bytes(b"synthetic-cache")
            self.assertTrue(is_excluded(ROOT, cached))
            self.assertEqual(manifest_payload(ROOT), baseline)

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
        english = LANDING_EN.read_text(encoding="utf-8")
        style = LANDING_STYLE.read_text(encoding="utf-8")
        self.assertIn('<html lang="uk">', landing)
        self.assertIn('<html lang="en">', english)
        self.assertIn('href="en.html"', landing)
        self.assertIn('href="index.html"', english)
        for page in (landing, english):
            scripts = re.findall(r'<script\s+src="([^"]+)"\s+defer></script>', page)
            self.assertEqual(scripts, ["proof-experience.js", "intake-experience.js", "operating-core-experience.js"])
            self.assertEqual(page.lower().count("<script"), 4)
            self.assertNotIn("<form", page.lower())
            self.assertNotIn("http://", page.lower())
            self.assertNotRegex(page, r"(?:/home/|\.openclaw|Дзеркало|Комната поля|Omnigen)")
            self.assertEqual(
                set(re.findall(r'https://[^"< ]+', page)),
                {
                    "https://github.com/DiadkoShmek/evidence-gated-agent-workflows",
                    "https://github.com/DiadkoShmek/evidence-gated-agent-workflows/issues/new?template=client-inquiry.yml",
                    "https://diadkoshmek.github.io/evidence-gated-agent-workflows/",
                    "https://diadkoshmek.github.io/evidence-gated-agent-workflows/en.html",
                    "https://schema.org",
                },
            )
            main = re.search(r"<main\b.*?</main>", page, re.DOTALL)
            self.assertIsNotNone(main)
            self.assertEqual(main.group(0).count("$1,500"), 1)  # type: ignore[union-attr]
            self.assertLess(len(page.encode("utf-8")), 32 * 1024)
        self.assertTrue(PROOF_EXPERIENCE.is_file())
        self.assertIn("AI Systems Proof Sprint · фіксований інженерний спринт", landing)
        self.assertIn("AI Systems Proof Sprint · 3–5 day fixed-scope engineering sprint", english)
        self.assertIn("does not prove", english)
        self.assertIn("Ілюстративне browser-local відтворення", landing)
        self.assertNotIn("url(", style.lower())
        self.assertNotIn("@import", style.lower())
        for page in (landing, english):
            resource_urls = re.findall(r'<link rel="stylesheet" href="([^"]+)">', page)
            resource_urls += re.findall(r'<script src="([^"]+)" defer></script>', page)
            self.assertEqual(resource_urls, ["styles.css", "proof-experience.js", "intake-experience.js", "operating-core-experience.js"])
            self.assertNotRegex(page.lower(), r'<link\b[^>]*\brel="?preload\b')
        self.assertLess(len(LANDING_STYLE.read_bytes()), 32 * 1024)

    def test_bilingual_discovery_metadata_is_exact_static_and_scope_bound(self) -> None:
        base = "https://diadkoshmek.github.io/evidence-gated-agent-workflows/"
        issue_url = "https://github.com/DiadkoShmek/evidence-gated-agent-workflows/issues/new?template=client-inquiry.yml"
        repository_url = "https://github.com/DiadkoShmek/evidence-gated-agent-workflows"
        expected_by_page = (
            (
                LANDING.read_text(encoding="utf-8"),
                {
                    "language": "uk",
                    "title": "AI Systems Proof Sprint — Артур Онисько",
                    "description": "AI Systems Proof Sprint: фіксований $1,500 sprint на 3–5 днів для однієї AI або data передачі: fail-closed provenance adapter, hostile proof і review-only handoff.",
                    "canonical": base,
                },
            ),
            (
                LANDING_EN.read_text(encoding="utf-8"),
                {
                    "language": "en",
                    "title": "AI Systems Proof Sprint — Artur Onysko",
                    "description": "AI Systems Proof Sprint: a $1,500, 3–5 day fixed-scope sprint for one AI or data workflow, delivered as a fail-closed provenance adapter, hostile proof, and review-only handoff.",
                    "canonical": base + "en.html",
                },
            ),
        )
        for page, expected in expected_by_page:
            head = re.search(r"<head>(.*?)</head>", page, re.DOTALL)
            self.assertIsNotNone(head)
            head_markup = head.group(1)  # type: ignore[union-attr]
            self.assertIn(f"<title>{expected['title']}</title>", head_markup)
            self.assertIn(f'<meta name="description" content="{expected["description"]}">', head_markup)
            self.assertIn(f'<link rel="canonical" href="{expected["canonical"]}">', head_markup)
            self.assertEqual(
                re.findall(r'<link rel="alternate" hreflang="([^"]+)" href="([^"]+)">', head_markup),
                [("uk", base), ("en", base + "en.html"), ("x-default", base + "en.html")],
            )
            for property_name, content in (
                ("og:type", "website"),
                ("og:site_name", "AI Systems Proof Sprint"),
                ("og:title", expected["title"]),
                ("og:description", expected["description"]),
                ("og:url", expected["canonical"]),
            ):
                self.assertIn(f'<meta property="{property_name}" content="{content}">', head_markup)
            for name, content in (
                ("twitter:card", "summary"),
                ("twitter:title", expected["title"]),
                ("twitter:description", expected["description"]),
            ):
                self.assertIn(f'<meta name="{name}" content="{content}">', head_markup)
            structured_match = re.search(
                r'<script type="application/ld\+json">(.*?)</script>', head_markup, re.DOTALL,
            )
            self.assertIsNotNone(structured_match)
            self.assertEqual(
                json.loads(structured_match.group(1)),  # type: ignore[union-attr]
                {
                    "@context": "https://schema.org",
                    "@type": "Service",
                    "name": "AI Systems Proof Sprint",
                    "description": expected["description"],
                    "url": expected["canonical"],
                    "inLanguage": expected["language"],
                    "provider": {"@type": "Person", "name": "Artur Onysko"},
                    "offers": {"@type": "Offer", "price": "1500", "priceCurrency": "USD"},
                },
            )
            self.assertNotRegex(head_markup.lower(), r"(?:analytics|gtag|plausible|pixel|og:image|twitter:image)")
            self.assertEqual(
                set(re.findall(r"https://[^\"<\s]+", page)),
                {base, base + "en.html", "https://schema.org", repository_url, issue_url},
            )

    def test_buyer_visible_progression_keeps_only_the_first_sprint_purchasable(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        landing = LANDING_EN.read_text(encoding="utf-8")
        progression = re.search(
            r'<section class="section shell progression".*?</section>', landing, re.DOTALL,
        )
        self.assertIsNotNone(progression)
        progression_text = progression.group(0)  # type: ignore[union-attr]
        for text in (
            "A staged system, with one purchasable first step",
            "one fail-closed handoff",
            "After Stage 1 evidence — separately scoped hardening",
            "After evidence — operator system roadmap",
        ):
            self.assertIn(text, readme)
        for text in (
            "The only purchasable step is the fixed sprint above.",
            "One fail-closed handoff",
            "Harden an agent/runtime control plane",
            "Operator system roadmap",
            "It is not included, priced, or promised by the first sprint.",
            "It does not authorize implementation.",
        ):
            self.assertIn(text, progression_text)
        buyer_visible_main = re.search(r"<main\b.*?</main>", landing, re.DOTALL)
        self.assertIsNotNone(buyer_visible_main)
        self.assertEqual(buyer_visible_main.group(0).count("$1,500"), 1)  # type: ignore[union-attr]
        for cautious_clause in (
            "Later layers are considered only when its written evidence identifies a real boundary worth carrying forward.",
            "A later written scope may harden the boundary the sprint exposes.",
            "It is not included, priced, or promised by the first sprint.",
            "It does not authorize implementation.",
        ):
            self.assertIn(cautious_clause, progression_text)
        prohibited_claim_patterns = (
            r"\b(?:client|customer)\s+(?:results?|outcomes?|success(?:es)?|impact)\b",
            r"\b(?:production|live)\s+(?:operation|operations|operating|deployment|deployed|system)\b",
            r"\b(?:security|certification|compliance)\b",
            r"\b(?:enterprise|platform)\s+(?:ready|readiness|grade|scale|scaling)\b",
            r"\b(?:guaranteed?|assured|proven)\s+(?:outcomes?|results?|success(?:es)?|improvement)\b",
            r"\b(?:deployed|running)\s+(?:systems?|platform|control plane)\b",
            r"\b(?:team|agent)s?\s+(?:scale|scaling|fleet|at scale)\b",
            r"\b(?:market[- ]?(?:leader|leading)|superior|best[- ]in[- ]class)\b",
        )
        for pattern in prohibited_claim_patterns:
            self.assertNotRegex(progression_text.lower(), pattern)

    def test_operating_core_map_has_exact_bilingual_stage_machine_and_one_purchasable_step(self) -> None:
        ukrainian = LANDING.read_text(encoding="utf-8")
        english = LANDING_EN.read_text(encoding="utf-8")
        expected_stages = [
            "system-boundary", "evidence-decision", "bounded-lifecycle",
            "human-authority", "receipt-handoff",
        ]
        for page in (ukrainian, english):
            section = re.search(r'<section id="operating-core".*?</section>', page, re.DOTALL)
            self.assertIsNotNone(section)
            markup = section.group(0)  # type: ignore[union-attr]
            self.assertEqual(re.findall(r'data-core-stage="([a-z-]+)"', markup), expected_stages)
            self.assertEqual(
                re.findall(r'data-core-stage="[a-z-]+" aria-pressed="(true|false)"', markup),
                ["true", "false", "false", "false", "false"],
            )
            for field in (
                "stage-id", "title", "reference", "buyer", "limit", "authority",
                "external", "production", "provider",
            ):
                self.assertIn(f"data-core-{field}", markup)
        self.assertIn("Перший slice operating core, не chatbot-проєкт.", ukrainian)
        self.assertIn("The first slice of an operating core, not a chatbot project.", english)
        self.assertIn("Єдиний purchasable крок зараз — fixed sprint вище.", ukrainian)
        self.assertIn("The fixed sprint above remains the only purchasable step now.", english)

    def test_operating_core_runtime_replays_all_stages_and_static_bootstrap_exactly(self) -> None:
        expected_controls = [
            "system-boundary", "evidence-decision", "bounded-lifecycle",
            "human-authority", "receipt-handoff",
        ]
        expected_copy = {
            "en": {
                "system-boundary": ("System boundary", "Typed source-to-target boundary", "Named source, target, owner, and schema", "No client-system access or production."),
                "evidence-decision": ("Evidence decision", "Fail-closed decision trace", "Agreed valid and hostile fixtures", "No client evidence or certification claim."),
                "bounded-lifecycle": ("Bounded lifecycle", "Fingerprint, bounded retries, terminal states", "Platform version and test environment", "No live worker or multi-writer claim."),
                "human-authority": ("Human authority", "Named human decision boundary", "Human-approved action and decision owner", "No automatic activation or external action."),
                "receipt-handoff": ("Receipt / handoff", "Fixture hashes, decision, and known limits", "Reviewable handoff and next-sprint decision", "No provider observation or production receipt."),
            },
            "uk": {
                "system-boundary": ("Межа системи", "Typed source-to-target boundary", "Названі source, target, owner та schema", "Немає доступу до client system чи production."),
                "evidence-decision": ("Evidence decision", "Fail-closed decision trace", "Погоджені valid та hostile fixtures", "Немає client evidence чи certification claim."),
                "bounded-lifecycle": ("Bounded lifecycle", "Fingerprint, bounded retries, terminal states", "Platform version і test environment", "Немає live worker чи multi-writer claim."),
                "human-authority": ("Людська влада", "Named human decision boundary", "Human-approved action і decision owner", "Немає automatic activation чи external action."),
                "receipt-handoff": ("Receipt / handoff", "Fixture hashes, decision і known limits", "Reviewable handoff і next-sprint decision", "Немає provider observation чи production receipt."),
            },
        }
        pages = {"en": LANDING_EN.read_text(encoding="utf-8"), "uk": LANDING.read_text(encoding="utf-8")}
        for language, page in pages.items():
            replay = replay_operating_core_map_dom(language)
            snapshots = {"system-boundary": replay["initial"], **replay["stages"]}
            self.assertEqual(list(replay["stages"]), expected_controls)
            for stage in expected_controls:
                snapshot = snapshots[stage]
                title, reference, buyer, limit = expected_copy[language][stage]
                self.assertEqual(
                    (snapshot["stage"], snapshot["title"], snapshot["reference"], snapshot["buyer"], snapshot["limit"]),
                    (stage, title, reference, buyer, limit),
                )
                self.assertEqual(
                    (snapshot["authority"], snapshot["external"], snapshot["production"], snapshot["provider"]),
                    ("none", "false", "false", "false"),
                )
                self.assertEqual([control["id"] for control in snapshot["controls"]], expected_controls)
                selected = [control for control in snapshot["controls"] if control["classSelected"]]
                self.assertEqual(selected, [{"id": stage, "classSelected": True, "ariaPressed": "true"}])
                self.assertEqual(
                    [control["ariaPressed"] for control in snapshot["controls"]],
                    ["true" if control["id"] == stage else "false" for control in snapshot["controls"]],
                )
            static = {}
            for field, tag in (
                ("stage", "dd"), ("title", "h3"), ("reference", "dd"), ("buyer", "dd"),
                ("limit", "dd"), ("authority", "dd"), ("external", "dd"),
                ("production", "dd"), ("provider", "dd"),
            ):
                attribute = "stage-id" if field == "stage" else field
                match = re.search(rf'data-core-{attribute}>([^<]+)</{tag}>', page)
                self.assertIsNotNone(match, field)
                static[field] = match.group(1)  # type: ignore[union-attr]
            expected_static = {
                key: snapshots["system-boundary"][key]
                for key in ("stage", "title", "reference", "buyer", "limit", "authority", "external", "production", "provider")
            }
            self.assertEqual(static, expected_static)
        source = OPERATING_CORE_EXPERIENCE.read_text(encoding="utf-8").lower()
        for forbidden in (
            "fetch(", "xmlhttprequest", "sendbeacon", "clipboard", "window.location",
            "document.location", "urlsearchparams", "window.history", "window.open",
            "location.assign", "location.replace", "history.pushstate", "history.replacestate",
            "prefill", "serviceworker", "caches", "localstorage", "sessionstorage",
            "indexeddb", "document.cookie", "websocket", "eventsource", "http://",
            "https://", "import ", "import(",
        ):
            self.assertNotIn(forbidden, source)

    def test_failure_trace_explorer_replays_only_checked_in_synthetic_outcomes(self) -> None:
        landing = LANDING.read_text(encoding="utf-8")
        experience = PROOF_EXPERIENCE.read_text(encoding="utf-8")
        for scenario in ("clean", "missing", "stale", "conflict", "risk"):
            outcome = evaluate_evidence_fixture(scenario)
            self.assertFalse(outcome["external_action_authorized"])
            trace_pattern = re.compile(
                rf'id: "{scenario}".*?'
                rf'outcome: "{outcome["decision"]}".*?'
                rf'reason: "{outcome["reason"]}".*?'
                rf'fixtureDecision: "{outcome["decision"]}".*?'
                r'externalActionAuthorized: false',
                re.DOTALL,
            )
            self.assertRegex(experience, trace_pattern)
            self.assertIn(f'data-trace-scenario="{scenario}"', landing)
        self.assertEqual(experience.count('externalActionAuthorized: false'), 5)
        self.assertIn("окремих зафіксованих <code>evidence-gate</code> fixtures", landing)
        self.assertIn("Поточний source explorer не має network, storage або telemetry APIs", landing)
        self.assertIn("Це не Python equivalence, EGOH parity, production safety, certification, client validity чи external authorization", landing)

    def test_failure_trace_initial_dom_matches_canonical_clean_fixture(self) -> None:
        landing = LANDING_EN.read_text(encoding="utf-8")
        experience = PROOF_EXPERIENCE.read_text(encoding="utf-8")
        clean = evaluate_evidence_fixture("clean")
        expected = {
            "title": "Valid evidence",
            "outcome": clean["decision"],
            "reason": clean["reason"],
            "decision": clean["decision"],
            "authorized": canonical_json(clean["external_action_authorized"]),
            "explanation": "Complete synthetic evidence can produce a draft; a human still decides any next action.",
        }
        tags = {
            "title": "h3", "outcome": "dd", "reason": "dd", "decision": "dd",
            "authorized": "dd", "explanation": "p",
        }
        actual: dict[str, str] = {}
        for field, tag in tags.items():
            match = re.search(rf"data-trace-{field}>([^<]+)</{tag}>", landing)
            self.assertIsNotNone(match, field)
            actual[field] = match.group(1)  # type: ignore[union-attr]
        self.assertEqual(actual, expected)
        selected = re.findall(
            r'<button[^>]+data-trace-scenario="([^"]+)"[^>]+aria-pressed="true"',
            landing,
        )
        self.assertEqual(selected, ["clean"])
        initial_render = 'renderTrace(traceById.get("clean"));'
        click_binding = "traceControls.forEach((control) => {\n  control.addEventListener"
        self.assertIn(initial_render, experience)
        self.assertIn(click_binding, experience)
        self.assertLess(
            experience.index(initial_render),
            experience.index(click_binding),
        )

    def test_ukrainian_failure_trace_static_bootstrap_is_complete_and_selected_clean(self) -> None:
        landing = LANDING.read_text(encoding="utf-8")
        clean = evaluate_evidence_fixture("clean")
        expected = {
            "title": "Валідний доказ",
            "outcome": clean["decision"],
            "reason": clean["reason"],
            "decision": clean["decision"],
            "authorized": canonical_json(clean["external_action_authorized"]),
            "explanation": "Повний синтетичний доказ може дати draft; будь-яку наступну дію все одно вирішує людина.",
        }
        tags = {
            "title": "h3", "outcome": "dd", "reason": "dd", "decision": "dd",
            "authorized": "dd", "explanation": "p",
        }
        actual: dict[str, str] = {}
        for field, tag in tags.items():
            match = re.search(rf"data-trace-{field}>([^<]+)</{tag}>", landing)
            self.assertIsNotNone(match, field)
            actual[field] = match.group(1)  # type: ignore[union-attr]
        self.assertEqual(actual, expected)
        self.assertEqual(
            re.findall(
                r'<button[^>]+data-trace-scenario="([^"]+)"[^>]+aria-pressed="(true|false)"[^>]*>([^<]+)</button>',
                landing,
            ),
            [
                ("clean", "true", "Валідний доказ"),
                ("missing", "false", "Відсутній доказ"),
                ("stale", "false", "Застарілий доказ"),
                ("conflict", "false", "Суперечливий доказ"),
                ("risk", "false", "Передача з risk-tag"),
            ],
        )
        for label in (
            "Зафіксований синтетичний результат",
            "Результат triage",
            "Названа причина",
            "Рішення fixture",
            "Зовнішня дія дозволена",
            "Ілюстративне browser-local відтворення окремих зафіксованих <code>evidence-gate</code> fixtures.",
            "Поточний source explorer не має network, storage або telemetry APIs.",
        ):
            self.assertIn(label, landing)

    def test_failure_trace_runtime_initializes_clean_and_replays_risk(self) -> None:
        replay = replay_failure_trace_explorer_dom("en")
        self.assertEqual(
            replay["initial"],
            {
                "title": "Valid evidence",
                "outcome": "draft",
                "reason": "EVIDENCE_COMPLETE",
                "decision": "draft",
                "authorized": "false",
                "explanation": (
                    "Complete synthetic evidence can produce a draft; "
                    "a human still decides any next action."
                ),
                "controls": [
                    {"id": "clean", "classSelected": True, "ariaPressed": "true"},
                    {"id": "missing", "classSelected": False, "ariaPressed": "false"},
                    {"id": "stale", "classSelected": False, "ariaPressed": "false"},
                    {"id": "conflict", "classSelected": False, "ariaPressed": "false"},
                    {"id": "risk", "classSelected": False, "ariaPressed": "false"},
                ],
            },
        )
        self.assertEqual(
            replay["risk"],
            {
                "title": "Risk-tagged handoff",
                "outcome": "escalate",
                "reason": "HUMAN_AUTHORITY_REQUIRED",
                "decision": "escalate",
                "authorized": "false",
                "explanation": (
                    "A financial risk tag escalates the decision to a human; "
                    "no action is authorized."
                ),
                "controls": [
                    {"id": "clean", "classSelected": False, "ariaPressed": "false"},
                    {"id": "missing", "classSelected": False, "ariaPressed": "false"},
                    {"id": "stale", "classSelected": False, "ariaPressed": "false"},
                    {"id": "conflict", "classSelected": False, "ariaPressed": "false"},
                    {"id": "risk", "classSelected": True, "ariaPressed": "true"},
                ],
            },
        )

    def test_bilingual_trace_runtime_has_one_five_case_parity_path(self) -> None:
        english = replay_failure_trace_explorer_dom("en")
        ukrainian = replay_failure_trace_explorer_dom("uk")
        experience = PROOF_EXPERIENCE.read_text(encoding="utf-8")
        self.assertIn('const TRACE_CASES = Object.freeze([', experience)
        self.assertIn('const TRACE_COPY = Object.freeze({', experience)
        self.assertEqual(experience.count('externalActionAuthorized: false'), 5)
        for snapshot in (english["initial"], english["risk"], ukrainian["initial"], ukrainian["risk"]):
            self.assertEqual(snapshot["authorized"], "false")
            self.assertEqual(snapshot["controls"], [
                {"id": "clean", "classSelected": snapshot["title"] in {"Valid evidence", "Валідний доказ"}, "ariaPressed": "true" if snapshot["title"] in {"Valid evidence", "Валідний доказ"} else "false"},
                {"id": "missing", "classSelected": False, "ariaPressed": "false"},
                {"id": "stale", "classSelected": False, "ariaPressed": "false"},
                {"id": "conflict", "classSelected": False, "ariaPressed": "false"},
                {"id": "risk", "classSelected": snapshot["title"] in {"Risk-tagged handoff", "Передача з risk-tag"}, "ariaPressed": "true" if snapshot["title"] in {"Risk-tagged handoff", "Передача з risk-tag"} else "false"},
            ])
        self.assertEqual(
            [(english["initial"][key], english["risk"][key]) for key in ("outcome", "reason", "decision", "authorized")],
            [(ukrainian["initial"][key], ukrainian["risk"][key]) for key in ("outcome", "reason", "decision", "authorized")],
        )
        self.assertEqual(ukrainian["initial"]["title"], "Валідний доказ")
        self.assertEqual(ukrainian["risk"]["title"], "Передача з risk-tag")

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

    def test_acceptance_packet_builder_is_bilingual_controlled_and_manual_only(self) -> None:
        ukrainian = LANDING.read_text(encoding="utf-8")
        english = LANDING_EN.read_text(encoding="utf-8")
        builder = INTAKE_EXPERIENCE.read_text(encoding="utf-8")
        expected_fields = [
            "workflow", "source", "target", "decision_owner_role", "costly_failure",
            "five_day_evidence", "test_environment", "human_action_boundary", "boundary_declaration",
        ]
        choices = re.compile(
            r'data-intake-field="([a-z_]+)" data-intake-value="([a-z0-9-]+)"'
        )
        self.assertEqual(choices.findall(ukrainian), choices.findall(english))
        self.assertEqual(
            list(dict.fromkeys(field for field, _value in choices.findall(ukrainian))),
            expected_fields,
        )
        self.assertEqual(len(choices.findall(ukrainian)), 23)
        for page in (ukrainian, english):
            self.assertIn('<script src="intake-experience.js" defer></script>', page)
            self.assertIn('data-intake-reset', page)
            self.assertIn('UNSENT · no buyer selections · local to this tab · not validated', page)
            self.assertIn('"external_action_authorized": false', page)
            self.assertIn('"authority": "none"', page)
            self.assertIn('"production_activation": "excluded"', page)
            self.assertNotRegex(page, r'<(?:form|input|select|textarea)\b')
            intake = re.search(r'<section id="intake".*?</section>', page, re.DOTALL)
            self.assertIsNotNone(intake)
            intake_markup = intake.group(0)  # type: ignore[union-attr]
            self.assertNotIn("is-selected", intake_markup)
            self.assertEqual(
                re.findall(r'data-intake-value="[^"]+" aria-pressed="([^"]+)"', intake_markup),
                ["false"] * 23,
            )
        self.assertIn("англомовну public GitHub Issue Form", ukrainian)
        self.assertIn("Public form не може перевірити відсутність private data", ukrainian)
        self.assertIn("English public GitHub Issue Form", english)
        self.assertIn("public form cannot verify the absence of private data", english)
        issue_href = (
            "https://github.com/DiadkoShmek/evidence-gated-agent-workflows/"
            "issues/new?template=client-inquiry.yml"
        )
        for page in (ukrainian, english):
            intake = re.search(r'<section id="intake".*?</section>', page, re.DOTALL)
            self.assertIsNotNone(intake)
            self.assertEqual(intake.group(0).count(issue_href), 1)  # type: ignore[union-attr]
            self.assertEqual(intake.group(0).count('data-issue-form-bridge'), 1)  # type: ignore[union-attr]
            self.assertIn('"state": "held-incomplete-local-draft"', intake.group(0))  # type: ignore[union-attr]
        for forbidden in (
            "fetch(", "xmlhttprequest", "sendbeacon", "clipboard", "window.location",
            "document.location", "urlsearchparams", "window.history", "window.open",
            "location.assign", "location.replace", "history.pushstate", "history.replacestate",
            "fragment", "prefill", "serviceworker", "caches",
            "localstorage", "sessionstorage", "indexeddb", "document.cookie", "websocket",
            "eventsource", "http://", "https://", "import ", "import(",
        ):
            self.assertNotIn(forbidden, builder.lower())

    def test_acceptance_packet_runtime_is_unsent_false_authority_and_resettable(self) -> None:
        replay = replay_acceptance_packet_builder_dom()
        initial = replay["initial"]
        partial = replay["partial"]
        complete = replay["complete"]
        reset = replay["reset"]
        self.assertIsInstance(initial, dict)
        self.assertIsInstance(partial, dict)
        self.assertIsInstance(complete, dict)
        self.assertEqual(reset, initial)
        initial_packet = initial["packet"]
        partial_packet = partial["packet"]
        complete_packet = complete["packet"]
        initial_bridge = initial["bridge"]
        partial_bridge = partial["bridge"]
        complete_bridge = complete["bridge"]
        self.assertEqual(initial_packet["schema"], "external-buyer-acceptance-packet-v1")
        self.assertEqual(
            initial_packet["output_status"],
            "UNSENT · no buyer selections · local to this tab · not validated",
        )
        self.assertEqual(initial_packet["scope"], "review-only")
        self.assertEqual(initial_packet["draft_class"], "unpopulated-planning-template")
        self.assertEqual(initial_packet["workflow"], None)
        self.assertEqual(initial_packet["completion_status"], "incomplete")
        self.assertEqual(partial_packet["costly_failure"], "contradictory-evidence")
        self.assertEqual(partial_packet["completion_status"], "incomplete")
        self.assertEqual(
            partial_packet["output_status"],
            "UNSENT · buyer-declared · local to this tab · not validated",
        )
        self.assertEqual(partial_packet["draft_class"], "buyer-declared-planning-draft")
        self.assertEqual(complete_packet["completion_status"], "complete-local-draft")
        self.assertEqual(complete_packet["workflow"], "agent-result-to-internal-tool")
        self.assertEqual(
            complete_packet["decision_owner_status"],
            "must-be-named-during-human-review",
        )
        self.assertEqual(
            complete_packet["exclusions"],
            "production-credentials-private-data-payment-account-changes-excluded",
        )
        self.assertEqual(
            complete_packet["output_status"],
            "UNSENT · buyer-declared · local to this tab · not validated",
        )
        self.assertEqual(complete_packet["draft_class"], "buyer-declared-planning-draft")
        for bridge in (initial_bridge, partial_bridge):
            self.assertEqual(bridge["schema"], "external-buyer-issue-form-bridge-v1")
            self.assertEqual(bridge["state"], "held-incomplete-local-draft")
            self.assertEqual(bridge["route"], "existing-github-issue-form")
            self.assertEqual(
                bridge["headings"],
                [
                    "One workflow", "Expensive failure", "Five-day proof",
                    "Test environment available?", "How did you find this sprint?",
                    "Public-data boundary",
                ],
            )
            self.assertIn("Choose all controlled planning values", bridge["reason"])
        self.assertEqual(complete_bridge["schema"], "external-buyer-issue-form-bridge-v1")
        self.assertEqual(complete_bridge["state"], "buyer-review-and-manual-entry-required")
        self.assertEqual(complete_bridge["route"], "existing-github-issue-form")
        self.assertEqual(
            [key for key in complete_bridge if key in {
                "One workflow", "Expensive failure", "Five-day proof",
                "Test environment available?", "How did you find this sprint?",
                "Public-data boundary",
            }],
            [
                "One workflow", "Expensive failure", "Five-day proof",
                "Test environment available?", "How did you find this sprint?",
                "Public-data boundary",
            ],
        )
        for heading, controlled_value in (
            ("One workflow", "agent result entering one internal tool"),
            ("Expensive failure", "missing evidence"),
            ("Five-day proof", "one valid fixture passes"),
        ):
            field = complete_bridge[heading]
            self.assertEqual(field["state"], "buyer-review-and-manual-entry-required")
            self.assertIn(controlled_value, field["scaffold"])
        self.assertEqual(
            complete_bridge["Test environment available?"],
            "Partly — examples only",
        )
        self.assertEqual(
            complete_bridge["How did you find this sprint?"],
            {
                "state": "buyer-selection-required-in-public-form",
                "options": [
                    "GitHub profile", "GitHub repository or release", "Search",
                    "Referral or recommendation", "Other public source",
                ],
                "attribution_class": "buyer-declared-not-authenticated",
            },
        )
        self.assertEqual(
            complete_bridge["Public-data boundary"],
            [
                {
                    "state": "buyer-review-and-manual-entry-required",
                    "manual_checkbox_label": "I confirm this issue contains no credentials, personal/customer data, private code, private URLs, or production access details.",
                },
                {
                    "state": "buyer-review-and-manual-entry-required",
                    "manual_checkbox_label": "I understand that production activation, credentials, payments, and account changes are outside the first public inquiry.",
                },
            ],
        )
        for bridge in (initial_bridge, partial_bridge, complete_bridge):
            for field in (
                "external_action_authorized", "issue_created", "provider_observed", "queue_admitted",
            ):
                self.assertIs(bridge[field], False)
            self.assertEqual(bridge["authority"], "none")
        for packet in (initial_packet, partial_packet, complete_packet):
            for field in (
                "evidence", "contract", "award", "payment", "external_action",
                "external_action_authorized", "production", "automatic_submit",
                "issue_created", "provider_observed", "queue_admitted",
            ):
                self.assertIs(packet[field], False)
            self.assertEqual(packet["authority"], "none")
            self.assertEqual(packet["production_activation"], "excluded")
            self.assertEqual(packet["manual_route"], "existing-github-issue-form")
            self.assertEqual(packet["issue_form_guidance"]["route"], packet["manual_route"])
            self.assertEqual(
                set(packet["issue_form_guidance"]),
                {
                    "route", "headings", "environment_mapping",
                    "manual_public_summary_required", "buyer_declared_acquisition_source_options",
                    "public_data_boundary_requirements",
                },
            )
            self.assertEqual(
                packet["issue_form_guidance"]["headings"],
                [
                    "One workflow", "Expensive failure", "Five-day proof",
                    "Test environment available?", "How did you find this sprint?",
                    "Public-data boundary",
                ],
            )
            self.assertEqual(
                packet["issue_form_guidance"]["environment_mapping"],
                {
                    "sanitized-test-environment": "Yes — sanitized test environment and examples",
                    "sanitized-example-only": "Partly — examples only",
                    "discovery-before-artifact": "No — discovery and contract first",
                },
            )
            self.assertEqual(
                packet["issue_form_guidance"]["manual_public_summary_required"],
                {
                    "workflow": "manual-public-summary-required",
                    "failure": "manual-public-summary-required",
                    "proof": "manual-public-summary-required",
                },
            )
            self.assertEqual(
                packet["issue_form_guidance"]["buyer_declared_acquisition_source_options"],
                [
                    "GitHub profile", "GitHub repository or release", "Search",
                    "Referral or recommendation", "Other public source",
                ],
            )
            self.assertEqual(
                set(packet["issue_form_guidance"]["manual_public_summary_required"]),
                {"workflow", "failure", "proof"},
            )
            self.assertEqual(
                set(packet["issue_form_guidance"]["public_data_boundary_requirements"].values()),
                {"manual-checkbox-attestation-required"},
            )
            self.assertNotIn(
                "manual-public-summary-required",
                packet["issue_form_guidance"]["public_data_boundary_requirements"].values(),
            )
            serialized_guidance = canonical_json(packet["issue_form_guidance"]).lower()
            for prohibited in ("authority", "admission", "created", "provider"):
                self.assertNotIn(prohibited, serialized_guidance)
        selected = [
            control for control in partial["controls"]
            if control["field"] == "costly_failure" and control["classSelected"]
        ]
        self.assertEqual(
            selected,
            [{
                "field": "costly_failure",
                "value": "contradictory-evidence",
                "classSelected": True,
                "ariaPressed": "true",
            }],
        )

    def test_public_inquiry_warns_without_claiming_enforced_sanitization(self) -> None:
        inquiry = INQUIRY.read_text(encoding="utf-8")
        self.assertIn("name: AI Systems Proof Sprint — scoped inquiry", inquiry)
        self.assertIn(
            "description: Describe one sanitized AI or data handoff for the fixed $1,500, 3–5 working day first step; this form is review-only.",
            inquiry,
        )
        self.assertIn("This is a public issue", inquiry)
        self.assertIn(
            "This review-only form is for the AI Systems Proof Sprint: one fixed $1,500, 3–5 working day first step delivering one fail-closed provenance adapter, hostile proof, and reviewable handoff.",
            inquiry,
        )
        self.assertIn(
            "Submitting this form does not purchase a sprint, accept a contract, reserve capacity, or authorize a production or external action.",
            inquiry,
        )
        for forbidden in ("email", "phone", "password", "token", "api key", "upload"):
            self.assertNotRegex(inquiry.lower(), rf"id:\s*{re.escape(forbidden)}")
        for required in ("id: workflow", "id: failure", "id: proof", "id: boundary"):
            self.assertIn(required, inquiry)
        self.assertIn("production activation", inquiry)
        self.assertIn("private code", inquiry)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("sanitized workflow inquiry", readme)

    def test_agent_action_demo_routes_manually_to_local_intake_without_prefill(self) -> None:
        readme = (ROOT / "agent-action-admission-demo" / "README.md").read_text(
            encoding="utf-8"
        )
        intake_url = (
            "https://diadkoshmek.github.io/"
            "evidence-gated-agent-workflows/en.html#intake"
        )
        self.assertEqual(readme.count(intake_url), 1)
        self.assertIn("manually select **Agent result to internal tool**", readme)
        self.assertIn("does not copy", readme)
        self.assertIn("prefill the public Issue Form", readme)
        self.assertIn("or submit anything", readme)
        self.assertIn("fresh Python process", readme)
        self.assertIn("caller-held and integrity-checked, not", readme)
        self.assertIn("authenticated storage", readme)
        self.assertIn("trusted caller can construct a different internally", readme)
        self.assertIn("consistent packet", readme)
        self.assertNotRegex(intake_url, r"[?&](?:workflow|failure|proof|boundary)=")

    def test_public_inquiry_binds_exact_first_sprint_intake_contract(self) -> None:
        inquiry = INQUIRY.read_text(encoding="utf-8")
        self.assertRegex(inquiry, re.compile(r'^title: "\[inquiry\] "$', re.MULTILINE))
        self.assertRegex(
            inquiry,
            re.compile(r'^labels: \["client-inquiry", "review-required"\]$', re.MULTILINE),
        )
        blocks = re.split(r"(?=^  - type: )", inquiry, flags=re.MULTILINE)
        controls: list[tuple[str, str, str, str]] = []
        for block in blocks:
            control_type = re.search(r"^  - type: ([^\n]+)$", block, re.MULTILINE)
            control_id = re.search(r"^    id: ([^\n]+)$", block, re.MULTILINE)
            label = re.search(r"^      label: ([^\n]+)$", block, re.MULTILINE)
            if control_type and control_id and label:
                controls.append((control_type.group(1), control_id.group(1), label.group(1), block))
        self.assertEqual(
            [(control_type, control_id, label) for control_type, control_id, label, _ in controls],
            [
                ("input", "workflow", "One workflow"),
                ("textarea", "failure", "Expensive failure"),
                ("textarea", "proof", "Five-day proof"),
                ("dropdown", "environment", "Test environment available?"),
                ("dropdown", "discovery", "How did you find this sprint?"),
                ("checkboxes", "boundary", "Public-data boundary"),
            ],
        )
        self.assertEqual(
            [
                control_id
                for _control_type, control_id, _label, block in controls
                if re.search(r"^    validations:\n      required: true$", block, re.MULTILINE)
            ],
            ["workflow", "failure", "proof", "environment", "discovery"],
        )
        dropdown = controls[3][3]
        self.assertEqual(
            re.findall(r'^        - "([^\n]+)"$', dropdown, re.MULTILINE),
            [
                "Yes — sanitized test environment and examples",
                "Partly — examples only",
                "No — discovery and contract first",
            ],
        )
        discovery = controls[4][3]
        self.assertEqual(
            re.findall(r'^        - "([^\n]+)"$', discovery, re.MULTILINE),
            [
                "GitHub profile",
                "GitHub repository or release",
                "Search",
                "Referral or recommendation",
                "Other public source",
            ],
        )
        self.assertIn("buyer-declared", discovery.lower())
        self.assertIn("not authenticated attribution", discovery.lower())
        checkboxes = controls[5][3]
        self.assertEqual(
            re.findall(r"^        - label: ([^\n]+)\n          required: true$", checkboxes, re.MULTILINE),
            [
                "I confirm this issue contains no credentials, personal/customer data, private code, private URLs, or production access details.",
                "I understand that production activation, credentials, payments, and account changes are outside the first public inquiry.",
            ],
        )
        self.assertEqual(checkboxes.count("required: true"), 2)

        bridge_source = INTAKE_EXPERIENCE.read_text(encoding="utf-8")
        bridge_match = re.search(
            r"const ISSUE_FORM_BRIDGE_CONTRACT_JSON = `(.*?)`;", bridge_source, re.DOTALL
        )
        self.assertIsNotNone(bridge_match)
        bridge = json.loads(bridge_match.group(1))  # type: ignore[union-attr]
        headings = [label for _kind, _id, label, _block in controls]
        environment_options = re.findall(r'^        - "([^\n]+)"$', dropdown, re.MULTILINE)
        boundary_statements = re.findall(
            r"^        - label: ([^\n]+)\n          required: true$", checkboxes, re.MULTILINE
        )
        self.assertEqual(
            bridge,
            {
                "schema": "external-buyer-issue-form-bridge-v1",
                "route": "existing-github-issue-form",
                "headings": headings,
                "environment_mapping": {
                    "sanitized-test-environment": environment_options[0],
                    "sanitized-example-only": environment_options[1],
                    "discovery-before-artifact": environment_options[2],
                },
                "buyer_declared_acquisition_source_options": [
                    "GitHub profile",
                    "GitHub repository or release",
                    "Search",
                    "Referral or recommendation",
                    "Other public source",
                ],
                "public_data_boundary_statements": boundary_statements,
            },
        )
        for controlled_mapping in (
            "WORKFLOW_SCAFFOLDS", "SOURCE_SCAFFOLDS", "TARGET_SCAFFOLDS",
            "FAILURE_SCAFFOLDS", "PROOF_SCAFFOLDS",
        ):
            self.assertIn(f"const {controlled_mapping} = Object.freeze", bridge_source)
        for forbidden in ("materialize(", "queue_admitted: true", "external_action_authorized: true"):
            self.assertNotIn(forbidden, bridge_source)

    def test_pages_deploys_only_sealed_static_directory(self) -> None:
        workflow = PAGES_WORKFLOW.read_text(encoding="utf-8")
        verify_block, deploy_block = workflow.split("\n  deploy:\n", 1)
        self.assertIn("needs: verify", workflow)
        self.assertIn("run: python3 run_proof.py", verify_block)
        self.assertIn("path: docs", verify_block)
        self.assertIn("contents: read", workflow)
        self.assertIn("pages: write", workflow)
        self.assertIn("id-token: write", workflow)
        self.assertNotIn("pull_request", workflow)
        self.assertNotRegex(workflow, r"uses:\s+actions/[^\s]+@v\d")
        self.assertIn("actions/configure-pages@45bfe0192ca1faeb007ade9deae92b16b8254a0d", verify_block)
        self.assertIn("actions/upload-pages-artifact@fc324d3547104276b827a68afc52ff2a11cc49c9", verify_block)
        self.assertIn("actions/deploy-pages@cd2ce8fcbc39b97be8ca5fce6e763baed58fa128", deploy_block)
        proof_step = "run: python3 run_proof.py"
        configure_step = "actions/configure-pages@45bfe0192ca1faeb007ade9deae92b16b8254a0d"
        upload_step = "actions/upload-pages-artifact@fc324d3547104276b827a68afc52ff2a11cc49c9"
        self.assertEqual(verify_block.count(proof_step), 1)
        self.assertEqual(verify_block.count(configure_step), 1)
        self.assertEqual(verify_block.count(upload_step), 1)
        self.assertLess(verify_block.index(proof_step), verify_block.index(configure_step))
        self.assertLess(verify_block.index(configure_step), verify_block.index(upload_step))
        self.assertNotIn("actions/configure-pages@", deploy_block)
        self.assertNotIn("actions/upload-pages-artifact@", deploy_block)
        self.assertNotIn("actions/checkout@", deploy_block)
        self.assertNotIn("setup-node", deploy_block)
        self.assertNotIn("run: python3 run_proof.py", deploy_block)
        workflow_permissions = workflow.split("\npermissions:\n", 1)[1].split("\n\nconcurrency:\n", 1)[0]
        self.assertEqual(workflow_permissions, "  contents: read")
        self.assertNotIn("pages: write", verify_block)
        self.assertNotIn("id-token: write", verify_block)
        deploy_permissions = deploy_block.split("    permissions:\n", 1)[1].split("    environment:\n", 1)[0]
        self.assertEqual(deploy_permissions, "      pages: write\n      id-token: write\n")
        self.assertNotIn("contents: write", deploy_permissions)

    def test_proof_contract_declares_and_provisions_node_runtime_exactly(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("Python 3.12 and Node 24.14.0", readme)
        self.assertIn("Python standard library and\nno installed packages", readme)
        self.assertIn("built-in `vm`, not npm or installed JavaScript packages", readme)
        expected_actions = (
            "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
            "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97",
            "actions/setup-node@820762786026740c76f36085b0efc47a31fe5020",
        )
        for workflow_path in (PROOF_WORKFLOW, PAGES_WORKFLOW):
            workflow = workflow_path.read_text(encoding="utf-8")
            for action in expected_actions:
                self.assertIn(f"uses: {action}", workflow)
            self.assertIn('python-version: "3.12"', workflow)
            self.assertIn('node-version: "24.14.0"', workflow)
            self.assertIn("run: python3 run_proof.py", workflow)
            self.assertLess(
                workflow.index("uses: actions/setup-node@820762786026740c76f36085b0efc47a31fe5020"),
                workflow.index("run: python3 run_proof.py"),
            )
            self.assertNotRegex(workflow, r"uses:\s+actions/[^\s]+@v\d")
        pages = PAGES_WORKFLOW.read_text(encoding="utf-8")
        proof = PROOF_WORKFLOW.read_text(encoding="utf-8")
        proof_permissions = proof.split("\npermissions:\n", 1)[1].split("\njobs:\n", 1)[0]
        self.assertEqual(proof_permissions, "  contents: read\n")
        self.assertNotIn("write", proof_permissions)
        self.assertNotIn("id-token", proof_permissions)
        for action in (
            "actions/configure-pages@45bfe0192ca1faeb007ade9deae92b16b8254a0d",
            "actions/upload-pages-artifact@fc324d3547104276b827a68afc52ff2a11cc49c9",
            "actions/deploy-pages@cd2ce8fcbc39b97be8ca5fce6e763baed58fa128",
        ):
            self.assertIn(f"uses: {action}", pages)
        combined = pages + proof
        for retired_pin in (
            "11d5960a326750d5838078e36cf38b85af677262",
            "a26af69be951a213d495a4c3e4e4022e16d87065",
            "49933ea5288caeca8642d1e84afbd3f7d6820020",
            "983d7736d9b0ae728b81ab479565c72886d7745b",
            "56afc609e74202658d3ffba0e8f6dda462b719fa",
            "d6db90164ac5ed86f2b6aed7e0febac5b3c0c03e",
        ):
            self.assertNotIn(retired_pin, combined)

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
            relative = str(path.relative_to(ROOT))
            for match in PRIVATE_MARKER.finditer(path.read_text(encoding="utf-8")):
                if relative in PUBLIC_CONTACT_PATHS and match.group(0).lower() == PUBLIC_CONTACT_EMAIL:
                    continue
                findings.append((relative, match.group(0)))
        self.assertEqual(findings, [])

    def test_egoh_candidate_contains_no_caches(self) -> None:
        excluded = [
            path.relative_to(ROOT)
            for path in EGOH.rglob("*")
            if path != MANIFEST and is_excluded(ROOT, path)
        ]
        self.assertEqual(excluded, [])


if __name__ == "__main__":
    unittest.main()
