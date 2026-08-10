"use strict";

const INTAKE_DEFAULTS = Object.freeze({
  workflow: null,
  source: null,
  target: null,
  decision_owner_role: null,
  costly_failure: null,
  five_day_evidence: null,
  test_environment: null,
  human_action_boundary: null,
  boundary_declaration: null,
});

const ISSUE_FORM_GUIDANCE_JSON = `{
  "route": "existing-github-issue-form",
  "headings": [
    "One workflow",
    "Expensive failure",
    "Five-day proof",
    "Test environment available?",
    "Public-data boundary"
  ],
  "environment_mapping": {
    "sanitized-test-environment": "Yes — sanitized test environment and examples",
    "sanitized-example-only": "Partly — examples only",
    "discovery-before-artifact": "No — discovery and contract first"
  },
  "manual_public_summary_required": {
    "workflow": "manual-public-summary-required",
    "failure": "manual-public-summary-required",
    "proof": "manual-public-summary-required"
  },
  "public_data_boundary_requirements": {
    "I confirm this issue contains no credentials, personal/customer data, private code, private URLs, or production access details.": "manual-checkbox-attestation-required",
    "I understand that production activation, credentials, payments, and account changes are outside the first public inquiry.": "manual-checkbox-attestation-required"
  }
}`;
const ISSUE_FORM_GUIDANCE = Object.freeze(JSON.parse(ISSUE_FORM_GUIDANCE_JSON));

const ISSUE_FORM_BRIDGE_CONTRACT_JSON = `{
  "schema": "external-buyer-issue-form-bridge-v1",
  "route": "existing-github-issue-form",
  "headings": [
    "One workflow",
    "Expensive failure",
    "Five-day proof",
    "Test environment available?",
    "Public-data boundary"
  ],
  "environment_mapping": {
    "sanitized-test-environment": "Yes — sanitized test environment and examples",
    "sanitized-example-only": "Partly — examples only",
    "discovery-before-artifact": "No — discovery and contract first"
  },
  "public_data_boundary_statements": [
    "I confirm this issue contains no credentials, personal/customer data, private code, private URLs, or production access details.",
    "I understand that production activation, credentials, payments, and account changes are outside the first public inquiry."
  ]
}`;
const ISSUE_FORM_BRIDGE_CONTRACT = Object.freeze(JSON.parse(ISSUE_FORM_BRIDGE_CONTRACT_JSON));

const WORKFLOW_SCAFFOLDS = Object.freeze({
  "agent-result-to-internal-tool": "an agent result entering one internal tool",
  "model-artifact-to-runtime": "a model artifact crossing into one runtime boundary",
  "async-job-status": "one asynchronous job status entering a review decision",
  "data-receipt": "one data receipt entering an internal review boundary",
});
const SOURCE_SCAFFOLDS = Object.freeze({
  "buyer-declared-sanitized-sample-artifact": "a buyer-declared sanitized sample artifact",
  "source-interface-description-only": "a source interface description only",
});
const TARGET_SCAFFOLDS = Object.freeze({
  "one-internal-review-boundary": "one internal review boundary",
  "one-bounded-runtime-adapter": "one bounded runtime adapter",
});
const FAILURE_SCAFFOLDS = Object.freeze({
  "missing-evidence": "missing evidence",
  "stale-evidence": "stale evidence",
  "malformed-artifact": "a malformed artifact",
  "contradictory-evidence": "contradictory evidence",
});
const PROOF_SCAFFOLDS = Object.freeze({
  "valid-fixture-plus-hostile-fail-closed": "one valid fixture passes while hostile fixtures fail closed with named reasons",
  "bounded-polling-terminal-state": "a bounded polling path reaches a named terminal state without inventing success",
  "decision-trace-known-limits": "a decision trace and known-limits report make the first boundary reviewable",
});

const intakeChoices = Array.from(document.querySelectorAll("[data-intake-field]"));
const intakePacket = document.querySelector("[data-intake-packet]");
const issueFormBridge = document.querySelector("[data-issue-form-bridge]");
const intakeReset = document.querySelector("[data-intake-reset]");
const intakeState = { ...INTAKE_DEFAULTS };

function buildIssueFormBridge(complete) {
  const environment = ISSUE_FORM_BRIDGE_CONTRACT.environment_mapping[intakeState.test_environment];
  if (!complete || !environment) {
    return {
      schema: ISSUE_FORM_BRIDGE_CONTRACT.schema,
      state: "held-incomplete-local-draft",
      route: ISSUE_FORM_BRIDGE_CONTRACT.route,
      headings: ISSUE_FORM_BRIDGE_CONTRACT.headings,
      reason: "Choose all controlled planning values before the manual Issue Form scaffold appears.",
      authority: "none",
      external_action_authorized: false,
      issue_created: false,
      provider_observed: false,
      queue_admitted: false,
    };
  }
  return {
    schema: ISSUE_FORM_BRIDGE_CONTRACT.schema,
    state: "buyer-review-and-manual-entry-required",
    route: ISSUE_FORM_BRIDGE_CONTRACT.route,
    "One workflow": {
      state: "buyer-review-and-manual-entry-required",
      scaffold: `Review whether ${WORKFLOW_SCAFFOLDS[intakeState.workflow]} from ${SOURCE_SCAFFOLDS[intakeState.source]} to ${TARGET_SCAFFOLDS[intakeState.target]} is the one public workflow to describe.`,
    },
    "Expensive failure": {
      state: "buyer-review-and-manual-entry-required",
      scaffold: `Review whether ${FAILURE_SCAFFOLDS[intakeState.costly_failure]} is the costly failure that the first boundary must hold instead of treating as success.`,
    },
    "Five-day proof": {
      state: "buyer-review-and-manual-entry-required",
      scaffold: `Review whether ${PROOF_SCAFFOLDS[intakeState.five_day_evidence]} is the observable five-day proof for this first slice.`,
    },
    "Test environment available?": environment,
    "Public-data boundary": ISSUE_FORM_BRIDGE_CONTRACT.public_data_boundary_statements.map((statement) => ({
      state: "buyer-review-and-manual-entry-required",
      manual_checkbox_label: statement,
    })),
    authority: "none",
    external_action_authorized: false,
    issue_created: false,
    provider_observed: false,
    queue_admitted: false,
  };
}

function buildIntakePacket() {
  const complete = Object.values(intakeState).every((value) => value !== null);
  const selected = Object.values(intakeState).some((value) => value !== null);
  return {
    schema: "external-buyer-acceptance-packet-v1",
    workflow: intakeState.workflow,
    source: intakeState.source,
    target: intakeState.target,
    decision_owner_role: intakeState.decision_owner_role,
    decision_owner_status: "must-be-named-during-human-review",
    costly_failure: intakeState.costly_failure,
    measurable_five_day_evidence: intakeState.five_day_evidence,
    test_environment: intakeState.test_environment,
    human_action_boundary: intakeState.human_action_boundary,
    boundary_declaration: intakeState.boundary_declaration,
    exclusions: "production-credentials-private-data-payment-account-changes-excluded",
    output_status: selected
      ? "UNSENT · buyer-declared · local to this tab · not validated"
      : "UNSENT · no buyer selections · local to this tab · not validated",
    scope: "review-only",
    draft_class: selected ? "buyer-declared-planning-draft" : "unpopulated-planning-template",
    completion_status: complete ? "complete-local-draft" : "incomplete",
    authority: "none",
    evidence: false,
    contract: false,
    award: false,
    payment: false,
    external_action: false,
    external_action_authorized: false,
    production: false,
    production_activation: "excluded",
    automatic_submit: false,
    manual_route: "existing-github-issue-form",
    issue_form_guidance: ISSUE_FORM_GUIDANCE,
    issue_created: false,
    provider_observed: false,
    queue_admitted: false,
  };
}

function renderIntakePacket() {
  const packet = buildIntakePacket();
  intakePacket.textContent = JSON.stringify(packet, null, 2);
  issueFormBridge.textContent = JSON.stringify(buildIssueFormBridge(packet.completion_status === "complete-local-draft"), null, 2);
  intakeChoices.forEach((choice) => {
    const selected = intakeState[choice.dataset.intakeField] === choice.dataset.intakeValue;
    choice.classList.toggle("is-selected", selected);
    choice.setAttribute("aria-pressed", String(selected));
  });
}

renderIntakePacket();

intakeChoices.forEach((choice) => {
  choice.addEventListener("click", () => {
    intakeState[choice.dataset.intakeField] = choice.dataset.intakeValue;
    renderIntakePacket();
  });
});

intakeReset.addEventListener("click", () => {
  Object.assign(intakeState, INTAKE_DEFAULTS);
  renderIntakePacket();
});
