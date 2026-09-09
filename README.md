# opena2a-standards

Organization-level files for the opena2a-standards repositories.

- `profile/README.md`: the organization profile.
- `GOVERNANCE.md`: how the specifications are governed.
- `HARNESS.md` and `harness/`: the spec-drift harness, a reusable workflow every family repository runs to fail its build when a shared definition drifts from its home.
- `.github/workflows/spec-drift.yml`: the reusable workflow; `family-drift.yml` the daily family verdict; `self-test.yml` the harness's own gate.
