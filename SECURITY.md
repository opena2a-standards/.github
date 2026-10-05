# Security policy

This policy is the default for every repository in the `opena2a-standards`
organization that does not carry a `SECURITY.md` of its own. The repositories
hold specifications, their JSON schemas, conformance suites and reference
verifiers. A defect in any of them can make every conforming implementation
unsafe, so we treat it as a vulnerability rather than as a bug.

## Reporting a vulnerability

Report privately. Open the **Security** tab of the affected repository and
use **Report a vulnerability**, which creates a draft security advisory that
only the maintainers and you can read. GitHub documents the form at
[Privately reporting a security vulnerability](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability).

If the form is not available on that repository, or the finding spans several
repositories, email [info@opena2a.org](mailto:info@opena2a.org), the contact
address published in [GOVERNANCE.md](./GOVERNANCE.md). Do not put the details
in a public issue, pull request or discussion until a fix is published.

A report is handled in the advisory thread, which is also where the timing of
public disclosure is agreed. If you want to be credited, say so in the report.
This document makes no response-time commitment beyond what
[GOVERNANCE.md](./GOVERNANCE.md) already makes.

## What a report should contain

- The repository, the file and the section, field or fixture concerned, with
  the commit or published version you read.
- What the text, schema or verifier allows that it should reject, or rejects
  that it should allow, and why that matters to an implementation.
- A way to observe it: a fixture, a byte sequence, a verifier invocation and
  its output, or a step-by-step reading of the specification that leads to the
  unsafe outcome.
- Whether you know of an implementation or deployment that is affected.

A finding without a way to observe it is still welcome. Say what you could not
verify rather than guessing.

## Scope

In scope:

- Specification text that leads a conforming implementation to an unsafe
  result: an ambiguous verification step, a missing check, a field an attacker
  can control, a canonicalization that two implementations can read
  differently.
- A JSON schema that accepts what the specification rejects, or rejects what
  it requires.
- A reference verifier in a conformance suite that accepts input the
  specification rejects, or rejects input the specification accepts.
- A conformance fixture whose expected verdict is wrong, so that a verifier
  passing the suite is wrong in the same way.
- The spec-drift harness in this repository ([HARNESS.md](./HARNESS.md)), when
  it reports green on drift it is meant to catch.

Out of scope here, and to be reported to the project that maintains them:

- Implementations maintained in other organizations, including OpenA2A's own
  tools, SDKs and services. Report those through the repository that maintains
  them. A finding that turns out to be a specification defect is routed here by
  the maintainers.
- Signature schemes, hash functions and other primitives the specifications
  cite rather than define. Report those to their maintainers; tell us as well
  if a specification's use of the primitive is what makes it exploitable.
- The web sites and the documentation site, unless the defect is in the
  specification text they reproduce.

## How fixes are published

Published specification text is not edited in place. A fix to a published
version is issued as a new version under the version rule each specification
states at the top of its `CHANGELOG.md`, with a changelog entry that names the
advisory, and the conformance suite gains or corrects the fixture that pins the
corrected behaviour. Where a specification maintains an errata directory, the
correction is also filed there as an erratum. A verifier or fixture fix lands
in the conformance suite together with the fixture that proves it, and the
shared definitions it touches are re-checked by the spec-drift harness.
