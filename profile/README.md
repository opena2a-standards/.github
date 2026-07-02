<p align="center">
  <img src="https://raw.githubusercontent.com/opena2a-org/.github/main/profile/opena2a-wordmark.png" alt="OpenA2A" width="500">
</p>

<h3 align="center">Standards</h3>

---

Open specifications for AI agent security: identity, trust credentials, threat models, behavioral governance, and the conformance suites that test them. Vendor-neutral. Apache 2.0 unless noted per repo.

- [Agent Identity Protocol (AIP)](https://github.com/opena2a-standards/agent-identity-protocol): open standard for AI agent identity, capabilities, and trust.
- [did:opena2a](https://github.com/opena2a-standards/did-method-opena2a): registry-mediated DID method for agents and agent infrastructure. Filed with the W3C DID Method Registry ([did-extensions#717](https://github.com/w3c/did-extensions/pull/717), pending review).
- [Agent Trust Protocol (ATP)](https://github.com/opena2a-standards/agent-trust-protocol): open standard for verifiable trust assertions about AI agents.
- [ATX](https://github.com/opena2a-standards/atx-spec): Agent Trust eXtension credential format and protocol architecture.
- [Agent Authorization Protocol (AAP)](https://github.com/opena2a-standards/agent-authorization-protocol): scoped, attested authorization; credentials never enter the agent's context.
- [Agent Threat Matrix](https://github.com/opena2a-standards/agent-threat-matrix): tactics and techniques for attacks on AI agent systems. 61 techniques across 9 tactics, evidence-graded, mapped to MITRE, ATLAS, and OWASP. MITRE submission in flight.
- [ABGS](https://github.com/opena2a-standards/agent-governance-spec): Agent Behavioral Governance Specification. What goes in a SOUL.md file.
- [AIIS Signatures](https://github.com/opena2a-standards/aiis-signatures): AI Injection Signature Standard. YARA-style signatures for AI agent prompt injections in web content.
- [OTel SemConv for agent identity](https://github.com/opena2a-standards/otel-semconv-agent-identity): OpenTelemetry semantic conventions for AI agent authorization observability.

Conformance suites:

- [ATX Conformance](https://github.com/opena2a-standards/atx-conformance): byte-pinned fixtures and Go + Python reference verifiers for ATX v1.0 and v1.1, with a cross-language JCS byte-agreement gate.
- [ATP Conformance](https://github.com/opena2a-standards/atp-conformance): fixtures and Go + Python reference verifiers for ATP v1.0.0-rc1.
- [AIP Conformance](https://github.com/opena2a-standards/aip-conformance): challenge-response fixtures and Go + Python reference verifiers for AIP.
- [A2A-IDF Conformance](https://github.com/opena2a-standards/a2a-idf-conformance): canonical conformance suite for A2A-IDF.
- [opena2a-parity](https://github.com/opena2a-standards/opena2a-parity): cross-CLI parity gate for the OpenA2A CLI fleet.

The specifications are documented, with runnable walkthroughs, at [specs.opena2a.org](https://specs.opena2a.org).

See [GOVERNANCE.md](https://github.com/opena2a-standards/.github/blob/main/GOVERNANCE.md) for how decisions are made and how to contribute. The catalog of all OpenA2A organizations and projects lives at [opena2a.org/projects](https://opena2a.org/projects).
