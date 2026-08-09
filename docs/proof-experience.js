"use strict";

// Five static checked-in fixture outcomes; display copy follows document lang.
const TRACE_CASES = Object.freeze([
  Object.freeze({ id: "clean", outcome: "draft", reason: "EVIDENCE_COMPLETE", fixtureDecision: "draft", externalActionAuthorized: false }),
  Object.freeze({ id: "missing", outcome: "hold", reason: "EVIDENCE_NOT_ADMISSIBLE", fixtureDecision: "hold", externalActionAuthorized: false }),
  Object.freeze({ id: "stale", outcome: "hold", reason: "EVIDENCE_NOT_ADMISSIBLE", fixtureDecision: "hold", externalActionAuthorized: false }),
  Object.freeze({ id: "conflict", outcome: "hold", reason: "EVIDENCE_NOT_ADMISSIBLE", fixtureDecision: "hold", externalActionAuthorized: false }),
  Object.freeze({ id: "risk", outcome: "escalate", reason: "HUMAN_AUTHORITY_REQUIRED", fixtureDecision: "escalate", externalActionAuthorized: false })
]);

const TRACE_COPY = Object.freeze({
  en: Object.freeze({
    clean: Object.freeze({ title: "Valid evidence", explanation: "Complete synthetic evidence can produce a draft; a human still decides any next action." }),
    missing: Object.freeze({ title: "Missing evidence", explanation: "The fixture omits required proof, so the handoff is held without a substitute claim." }),
    stale: Object.freeze({ title: "Stale evidence", explanation: "Evidence beyond its declared freshness window stays held for a new, bounded review." }),
    conflict: Object.freeze({ title: "Conflicting evidence", explanation: "Conflicting values are not promoted across the handoff; the case stays held for resolution." }),
    risk: Object.freeze({ title: "Risk-tagged handoff", explanation: "A financial risk tag escalates the decision to a human; no action is authorized." })
  }),
  uk: Object.freeze({
    clean: Object.freeze({ title: "Валідний доказ", explanation: "Повний synthetic evidence може дати draft; будь-яку наступну дію все одно вирішує людина." }),
    missing: Object.freeze({ title: "Відсутній доказ", explanation: "Fixture не містить потрібного proof, тому handoff утримується без substitute claim." }),
    stale: Object.freeze({ title: "Застарілий доказ", explanation: "Evidence поза declared freshness window лишається hold для нового bounded review." }),
    conflict: Object.freeze({ title: "Суперечливий доказ", explanation: "Conflicting values не отримують promotion через handoff; case лишається hold для resolution." }),
    risk: Object.freeze({ title: "Передача з risk-tag", explanation: "Financial risk tag передає decision людині; жодна дія не authorized." })
  })
});

const documentLanguage = document.documentElement && document.documentElement.lang === "uk" ? "uk" : "en";
const TRACE_SCENARIOS = Object.freeze(TRACE_CASES.map((trace) => Object.freeze({ ...trace, ...TRACE_COPY[documentLanguage][trace.id] })));
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

renderTrace(traceById.get("clean"));
traceControls.forEach((control) => {
  control.addEventListener("click", () => {
    const trace = traceById.get(control.dataset.traceScenario);
    if (trace) renderTrace(trace);
  });
});
