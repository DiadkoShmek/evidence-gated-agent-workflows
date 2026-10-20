# Reading path

The public entry should show one understandable decision before asking the visitor to inspect implementation detail.

- **Observed:** the landing page previously exposed the technical map and large planning JSON by default.
- **Intent:** a concise public portfolio with evidence available on demand.
- **Design decision:** keep the evidence-switch example visible; place the map and planning tool in native, initially closed disclosures. Do not remove their limits or change their execution rules.

Reading order: problem → small examples → one interactive evidence decision → optional technical detail → contact.

The evidence switch is the signature interaction: changing the input case changes the displayed decision and reason. Native disclosures must work with keyboard input and without motion. Both language versions retain the same runtime selectors and static fallbacks. No new dependencies, tracking or external actions are introduced.
