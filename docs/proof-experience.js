"use strict";

// Static, checked-in display data. This file does not load, store, or submit data.
const TRACE_SCENARIOS = Object.freeze([
  Object.freeze({
    "id": "clean",
    "title": "Valid evidence",
    "outcome": "draft",
    "reason": "EVIDENCE_COMPLETE",
    "fixtureDecision": "draft",
    "externalActionAuthorized": false,
    "explanation": "Complete synthetic evidence can produce a draft; a human still decides any next action."
  }),
  Object.freeze({
    "id": "missing",
    "title": "Missing evidence",
    "outcome": "hold",
    "reason": "EVIDENCE_NOT_ADMISSIBLE",
    "fixtureDecision": "hold",
    "externalActionAuthorized": false,
    "explanation": "The fixture omits required proof, so the handoff is held without a substitute claim."
  }),
  Object.freeze({
    "id": "stale",
    "title": "Stale evidence",
    "outcome": "hold",
    "reason": "EVIDENCE_NOT_ADMISSIBLE",
    "fixtureDecision": "hold",
    "externalActionAuthorized": false,
    "explanation": "Evidence beyond its declared freshness window stays held for a new, bounded review."
  }),
  Object.freeze({
    "id": "conflict",
    "title": "Conflicting evidence",
    "outcome": "hold",
    "reason": "EVIDENCE_NOT_ADMISSIBLE",
    "fixtureDecision": "hold",
    "externalActionAuthorized": false,
    "explanation": "Conflicting values are not promoted across the handoff; the case stays held for resolution."
  }),
  Object.freeze({
    "id": "risk",
    "title": "Risk-tagged handoff",
    "outcome": "escalate",
    "reason": "HUMAN_AUTHORITY_REQUIRED",
    "fixtureDecision": "escalate",
    "externalActionAuthorized": false,
    "explanation": "A financial risk tag escalates the decision to a human; no action is authorized."
  })
]);

const traceById = new Map(TRACE_SCENARIOS.map((trace) => [trace.id, trace]));
const traceControls = document.querySelectorAll("[data-trace-scenario]");
const traceTitle = document.querySelector("[data-trace-title]");
const traceOutcome = document.querySelector("[data-trace-outcome]");
const traceReason = document.querySelector("[data-trace-reason]");
const traceDecision = document.querySelector("[data-trace-decision]");
const traceAuthorized = document.querySelector("[data-trace-authorized]");
const traceExplanation = document.querySelector("[data-trace-explanation]");

function renderTrace(trace) {
  traceTitle.textContent = trace.title;
  traceOutcome.textContent = trace.outcome;
  traceReason.textContent = trace.reason;
  traceDecision.textContent = trace.fixtureDecision;
  traceAuthorized.textContent = String(trace.externalActionAuthorized);
  traceExplanation.textContent = trace.explanation;
  traceControls.forEach((control) => {
    const selected = control.dataset.traceScenario === trace.id;
    control.classList.toggle("is-selected", selected);
    control.setAttribute("aria-pressed", String(selected));
  });
}

traceControls.forEach((control) => {
  control.addEventListener("click", () => {
    const trace = traceById.get(control.dataset.traceScenario);
    if (trace) renderTrace(trace);
  });
});
