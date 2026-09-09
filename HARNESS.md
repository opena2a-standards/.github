# Spec-drift harness

An executable spec-versus-verifier drift gate for the opena2a-standards
family. It turns the family's drift class (five documents defining trust
levels, a schema requiring a field the spec calls dead, a verifier step the
suite admits it does not test) from a periodic reading exercise into a build
failure.

## How a repository uses it

One workflow file, one line:

```yaml
# .github/workflows/spec-drift.yml
name: spec-drift
on:
  pull_request:
  push:
    branches: [main]
permissions:
  contents: read
jobs:
  spec-drift:
    uses: opena2a-standards/.github/.github/workflows/spec-drift.yml@main
```

The job checks out every family repository at `main`, the caller at the
commit under test, and runs every check. It fails only on checks whose home
or inspected documents include the caller's own files; drift elsewhere in the
family is reported as a warning in the job summary. The full report is the
`spec-drift-report` artifact (`report.json`, `report.md`).

The family verdict, where any drift fails, runs daily in this repository
(`family-drift.yml`).

Observed on the first caller (did-method-opena2a, 2026-09-09): the check run is named
`spec-drift / spec-drift (caller)` and completes in about twenty seconds; that is the
context name to require once a repository's main is protected. The `@main` reference is deliberate: check data updates
centrally, in one place, and reaches every caller on its next run.

## Run it locally

```
mkdir family && for r in $(python3 -c 'import json;print(*json.load(open("harness/family.json"))["repos"])'); do
  git clone --quiet --depth 1 "https://github.com/opena2a-standards/$r" "family/$r"; done
python3 harness/spec_drift.py --family-dir family --scope family
```

python3 3.12 standard library only. No package install, no network inside
the harness, no hosted model.

Exit codes: `0` no in-scope drift, `1` in-scope drift, `2` harness error
(a family checkout is missing, a home file or heading cannot be found, a
check names an unknown kind). An error fails the job the same way drift
does: a precondition the gate cannot find is never a skip.

## The data model

- `harness/family.json`: the repositories and the reference they are read at.
- `harness/homes/<id>.json`: where a shared definition lives. A home is a
  POINTER (repository, file, heading, marker) into an existing specification.
  This repository holds pointers only; a definition's value lives in its
  specification, once, and a value copied here is a defect (the one-home rule). A home may carry a marker comment
  `<!-- opena2a-definition: <id> -->` under its heading, optionally followed
  by a fenced `json` block the harness reads (a scale, a bound, an exception
  list).
- `harness/checks/<id>.json`: one check per file. Each names its home, its
  assertion kind, the documents it inspects (by repository, file, JSON path
  or section, never a bare file-wide regex where a same-shaped grammar lives
  nearby), the sweep item it descends from, and the fix.

An inspection whose file globs match nothing is a harness error, so a renamed verifier turns the gate red rather than green; an inspection whose emptiness is legitimate says `may_be_empty`. A check that fits an existing kind is a data file and needs no code. A new
kind is code in `spec_drift.py` plus a planted-drift test.

## Assertion kinds

| kind | asserts |
|---|---|
| `table-matches-registry` | tuples read from other tables or prose regex pairs are a subset of, or equal to, the home table's tuples; a table inspection marked `if_present` passes when no table with those columns exists under the heading (the definition is not restated there) |
| `regex-count` | a pattern occurs exactly `expect` times (usually 0: a forbidden restatement) or at least `min` times (a required citation) in the inspected files or sections |
| `json-path-grammar` | every value at a JSON path, or every literal a regex extracts from text, matches the home grammar and, when a registry is named, its key is a row of the home table; with `value_from_home`, a value equals the home block's value unless the block lists it as an exception |
| `json-required-excludes` | no schema property whose description matches a pattern is listed in `required[]` |
| `enum-equal` | an enum reads the same in every source (schema enum, backticked prose list) |
| `citation-set-equal` | every item in an index cites a section, and the cited set equals the set the home paragraph names |

## Scope

A check is in a caller's scope when the caller owns the home, or when a
finding sits in one of the caller's files. A repository that is merely
inspected, with every finding elsewhere, sees the check as family drift, not
as its own red. The report prints, per failing check, which caller files put
it in scope (or that the caller owns the home), so a red job is always
reachable from the pull request that sees it. A harness error on a check
that inspects the caller is the caller's.

## Adding a check

1. Measure the drift at source (file and line on `main` of each repository).
2. If the definition has no home file yet, add `harness/homes/<id>.json`.
3. Add `harness/checks/<id>.json` with the expected verdict on today's trees.
4. Add the clean and planted fixtures under `harness/tests/` and run
   `python3 harness/tests/run_tests.py`.
5. Run the family verdict locally and confirm the RED and GREEN sets are the
   ones you measured. A check that reds on the wrong lines proves nothing.

## Ownership of a red

The failure message names the home section and the inspected file and line.
The fix is one of: bring the inspected document to the home's definition,
cite the home instead of restating it, or, when the home is wrong, change the
home and let every citer follow. Changing an inspected document to match a
wrong home is the drift this harness exists to stop.
