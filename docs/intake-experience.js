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

const intakeChoices = Array.from(document.querySelectorAll("[data-intake-field]"));
const intakePacket = document.querySelector("[data-intake-packet]");
const intakeReset = document.querySelector("[data-intake-reset]");
const intakeState = { ...INTAKE_DEFAULTS };

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
  };
}

function renderIntakePacket() {
  intakePacket.textContent = JSON.stringify(buildIntakePacket(), null, 2);
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
