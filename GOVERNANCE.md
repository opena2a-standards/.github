# Governance

This organization hosts open specifications and their conformance suites for AI agent security.

## Current state

`opena2a-standards` is currently maintained by OpenA2A under an open-contribution model. Anyone may file issues, propose changes, and submit pull requests against any specification or conformance suite in this organization. Maintainership for individual specs is held by the original spec authors, who merge changes after review.

## Open contribution

- Bug reports, clarifications, and editorial improvements: open a pull request directly.
- Substantive changes to a published specification: open an issue first describing the change, the use case, and the affected sections. Maintainers will route the discussion before a PR is merged.
- New specifications: open a proposal issue in this `.github` repo. Acceptance criteria are listed in [CONTRIBUTING.md](./CONTRIBUTING.md) once that document lands.

## Path to multi-stakeholder governance

The current single-maintainer-org model is a starting point, not the end state. As adoption grows and external stakeholders adopt these specifications in production, governance will evolve to reflect that. The Agent Threat Matrix is already governed independently of OpenA2A Inc and serves as the template for how that transition looks in practice.

Concretely, the path is:

1. **Today**: OpenA2A maintains the org; spec authors maintain their specs; contributions are reviewed by the original maintainers.
2. **As external adoption grows**: per-spec working groups with named external contributors, public meeting cadence where useful, and documented voting procedures for substantive changes.
3. **When sustained**: a multi-stakeholder steering body, vendor-neutral by membership, formed deliberately and only when external stakeholders exist to seat.

The brief governing this transition is to avoid premature formal structures. A steering committee with no external members to seat would be theater. We add governance overhead in response to actual external stake, not in anticipation of it.

## Specifications, conformance, and the line between

A specification in this org defines a contract. Its conformance suite tests whether an implementation honors that contract. The two are paired: a spec without conformance is unverifiable, and a conformance suite without a stable spec is untestable. Pull requests that change a spec without updating the conformance suite (or vice versa) will be returned for joint review.

## Code of conduct

Contributors are expected to act professionally and in good faith. Personal attacks, harassment, and discrimination are not tolerated. Maintainers may remove or block contributors who violate this standard. A formal Code of Conduct will be adopted before the first external working group forms.

## Contact

For governance questions or to propose a new specification, open an issue in this repo (`opena2a-standards/.github`) or reach the maintainers at [info@opena2a.org](mailto:info@opena2a.org).
