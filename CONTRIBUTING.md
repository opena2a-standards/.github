# Contributing

This document is the default for every repository in the `opena2a-standards`
organization that does not carry a `CONTRIBUTING.md` of its own. Where a
repository has one, read that first; it may add requirements specific to that
specification. How the organization is governed, and how contribution rights
evolve, is in [GOVERNANCE.md](./GOVERNANCE.md).
Vulnerabilities are reported privately, as [SECURITY.md](./SECURITY.md)
describes, never through a public issue or pull request.

## Two kinds of change

A **normative** change alters what a conforming implementation must, should or
may do: a wire format, a field, a verification step, a conformance level, a
trust-level scale, a schema constraint, an expected fixture verdict. An
**editorial** change alters how the same requirement is expressed: wording,
structure, examples, links, typos. If an implementation written against the
old text and one written against the new text can disagree, the change is
normative.

- Editorial change: open a pull request directly.
- Normative change to a published specification: open an issue first, in the
  specification's repository, describing the change, the use case and the
  affected sections. Maintainers route the discussion before a pull request is
  merged. A pull request that arrives without that issue is routed to one
  before it is merged.
- New specification: open a proposal issue in this repository
  (`opena2a-standards/.github`). The acceptance criteria are below.

## What a normative change needs

A specification defines a contract and its conformance suite tests that
contract. [GOVERNANCE.md](./GOVERNANCE.md) returns a pull request that changes
one without the other for joint review, so a normative change arrives with:

- **The fixture that pins it.** A conformance fixture, in the paired
  conformance suite, that passes under the new text and fails under the old,
  or a changed expected verdict with the reasoning in the pull request. A
  fixture's expected verdict is never changed to make a verifier pass; a
  verifier that disagrees with a correct fixture is a verifier bug.
- **The changelog entry.** Every specification keeps a `CHANGELOG.md` in the
  format it states at its top. The change goes under the unreleased heading,
  naming the section and the fixture.
- **The version step.** Each specification's `CHANGELOG.md` states the version
  rule it uses. Published text is not edited in place; a normative change
  ships as a new version under that rule, and the pull request says which
  step it is.
- **A green drift gate.** Family repositories run the spec-drift harness
  described in [HARNESS.md](./HARNESS.md). If the change moves a shared
  definition, change its home and let the documents that cite it follow;
  never edit a citing document to match a home that is wrong.
- **Updated reference verifiers**, where the suite ships them, so that each
  language's verifier reaches the same verdict on the new fixture.

## Running a conformance suite locally

Each conformance repository's `README.md` is the authority for its own
layout: where the fixtures and their expected verdicts live, which
specification version they are pinned to, and how to run the reference
verifiers or use the fixtures against your own implementation. In general:

1. Clone the conformance repository at the commit or tag its README names for
   the specification version you implement.
2. Follow the README's section on running the verifiers for the language you
   use, and confirm the reference verifiers reach the expected verdicts.
3. Run your own verifier over every fixture and compare its verdict with the
   expected one. Every disagreement is either a bug in your verifier or a
   finding against the suite; report the second kind as an issue, or privately
   as [SECURITY.md](./SECURITY.md) describes if it makes a passing verifier
   unsafe.

The spec-drift harness runs locally too; [HARNESS.md](./HARNESS.md) gives the
command, with a clone of each family repository and the Python standard
library only.

## Proposals that depend on an upstream body

Several specifications are also submitted to, or registered with, external
standards bodies. A proposal whose outcome depends on a decision that body has
not yet taken (an Internet-Draft revision under review, a registry request, a
liaison question) is recorded as **blocked upstream**: the issue says so and
carries the upstream reference (the draft name and revision, the registry
pull request, the mailing-list thread), and it is not merged ahead of that
decision. When the body decides, the issue is updated with the outcome and the
proposal proceeds, is revised to match, or is closed. The organization does
not ship text that an upstream decision may contradict.

## New specifications

A proposal issue in this repository is accepted when it shows:

- A contract the specification defines, and the conformance suite that will
  test it, paired from the first published version.
- That no specification in the organization already defines it; a shared
  definition has one home and is cited, not restated.
- Named maintainers willing to hold maintainership and review changes.
- A vendor-neutral design and an open license, Apache 2.0 unless the proposal
  argues for another.
- A `CHANGELOG.md` that states the version rule the specification uses.

## Licensing and conduct

Contributions are licensed under the repository's license, Apache 2.0 unless
the repository notes otherwise. The conduct expected of contributors, and
what maintainers do when it is not met, is in
[GOVERNANCE.md](./GOVERNANCE.md).
