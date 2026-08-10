"use strict";

const CORE_STAGES = Object.freeze([
  Object.freeze({ id: "system-boundary", reference: "typed-source-target-boundary", buyer: "named-source-target-owner-schema", limit: "no-client-system-access-or-production" }),
  Object.freeze({ id: "evidence-decision", reference: "fail-closed-decision-trace", buyer: "agreed-valid-and-hostile-fixtures", limit: "no-client-evidence-or-certification-claim" }),
  Object.freeze({ id: "bounded-lifecycle", reference: "fingerprint-bounded-retries-terminal-states", buyer: "platform-version-and-test-environment", limit: "no-live-worker-or-multi-writer-claim" }),
  Object.freeze({ id: "human-authority", reference: "named-human-decision-boundary", buyer: "human-approved-action-and-decision-owner", limit: "no-automatic-activation-or-external-action" }),
  Object.freeze({ id: "receipt-handoff", reference: "fixture-hashes-decision-and-known-limits", buyer: "reviewable-handoff-and-next-sprint-decision", limit: "no-provider-observation-or-production-receipt" }),
]);

const CORE_COPY = Object.freeze({
  en: Object.freeze({
    "system-boundary": Object.freeze({ title: "System boundary", reference: "Typed source-to-target boundary", buyer: "Named source, target, owner, and schema", limit: "No client-system access or production." }),
    "evidence-decision": Object.freeze({ title: "Evidence decision", reference: "Fail-closed decision trace", buyer: "Agreed valid and hostile fixtures", limit: "No client evidence or certification claim." }),
    "bounded-lifecycle": Object.freeze({ title: "Bounded lifecycle", reference: "Fingerprint, bounded retries, terminal states", buyer: "Platform version and test environment", limit: "No live worker or multi-writer claim." }),
    "human-authority": Object.freeze({ title: "Human authority", reference: "Named human decision boundary", buyer: "Human-approved action and decision owner", limit: "No automatic activation or external action." }),
    "receipt-handoff": Object.freeze({ title: "Receipt / handoff", reference: "Fixture hashes, decision, and known limits", buyer: "Reviewable handoff and next-sprint decision", limit: "No provider observation or production receipt." }),
  }),
  uk: Object.freeze({
    "system-boundary": Object.freeze({ title: "Межа системи", reference: "Typed source-to-target boundary", buyer: "Названі source, target, owner та schema", limit: "Немає доступу до client system чи production." }),
    "evidence-decision": Object.freeze({ title: "Evidence decision", reference: "Fail-closed decision trace", buyer: "Погоджені valid та hostile fixtures", limit: "Немає client evidence чи certification claim." }),
    "bounded-lifecycle": Object.freeze({ title: "Bounded lifecycle", reference: "Fingerprint, bounded retries, terminal states", buyer: "Platform version і test environment", limit: "Немає live worker чи multi-writer claim." }),
    "human-authority": Object.freeze({ title: "Людська влада", reference: "Named human decision boundary", buyer: "Human-approved action і decision owner", limit: "Немає automatic activation чи external action." }),
    "receipt-handoff": Object.freeze({ title: "Receipt / handoff", reference: "Fixture hashes, decision і known limits", buyer: "Reviewable handoff і next-sprint decision", limit: "Немає provider observation чи production receipt." }),
  }),
});

const coreControls = Array.from(document.querySelectorAll("[data-core-stage]"));
const coreStage = document.querySelector("[data-core-stage-id]");
const coreTitle = document.querySelector("[data-core-title]");
const coreReference = document.querySelector("[data-core-reference]");
const coreBuyer = document.querySelector("[data-core-buyer]");
const coreLimit = document.querySelector("[data-core-limit]");
const coreAuthority = document.querySelector("[data-core-authority]");
const coreExternal = document.querySelector("[data-core-external]");
const coreProduction = document.querySelector("[data-core-production]");
const coreProvider = document.querySelector("[data-core-provider]");
const coreById = new Map(CORE_STAGES.map((stage) => [stage.id, stage]));
const coreLanguage = CORE_COPY[document.documentElement.lang] ? document.documentElement.lang : "en";

function renderCore(stage) {
  const copy = CORE_COPY[coreLanguage][stage.id];
  coreStage.textContent = stage.id;
  coreTitle.textContent = copy.title;
  coreReference.textContent = copy.reference;
  coreBuyer.textContent = copy.buyer;
  coreLimit.textContent = copy.limit;
  coreAuthority.textContent = "none";
  coreExternal.textContent = "false";
  coreProduction.textContent = "false";
  coreProvider.textContent = "false";
  coreControls.forEach((control) => {
    const selected = control.dataset.coreStage === stage.id;
    control.classList.toggle("is-selected", selected);
    control.setAttribute("aria-pressed", String(selected));
  });
}

renderCore(coreById.get("system-boundary"));

coreControls.forEach((control) => {
  control.addEventListener("click", () => {
    renderCore(coreById.get(control.dataset.coreStage));
  });
});
