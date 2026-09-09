#!/usr/bin/env python3
"""Spec-drift harness for the opena2a-standards family.

Checks are data (harness/checks/*.json). Homes are pointers into the
existing specifications (harness/homes/*.json), never values. The harness
reads a directory that holds one checkout per family repository
(--family-dir/<repo>) and reports every check; the exit code follows the
caller-scoped verdict:

  0  no in-scope drift
  1  in-scope drift (or, with --scope family, any drift)
  2  harness error: a family checkout is missing, a home file or heading
     cannot be found, or a check names an unknown assertion kind

python3 standard library only. See HARNESS.md.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
KINDS = (
    "table-matches-registry",
    "regex-count",
    "json-path-grammar",
    "json-required-excludes",
    "enum-equal",
    "citation-set-equal",
)
MARKER = "<!-- opena2a-definition: {id} -->"


class HarnessError(Exception):
    """A precondition the gate cannot find. Never a skip."""


# ---------------------------------------------------------------- loading


def load_json(path: Path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_family(family_file: Path) -> dict:
    fam = load_json(family_file)
    if not fam.get("repos"):
        raise HarnessError(f"{family_file}: no repos listed")
    return fam


def load_homes() -> dict:
    homes = {}
    for p in sorted((HERE / "homes").glob("*.json")):
        h = load_json(p)
        homes[h["id"]] = h
    return homes


def load_checks(only=None) -> list:
    checks = []
    seen = set()
    for p in sorted((HERE / "checks").glob("*.json")):
        c = load_json(p)
        seen.add(c["id"])
        if only and c["id"] not in only:
            continue
        if c.get("kind") not in KINDS:
            raise HarnessError(f"{p.name}: unknown assertion kind {c.get('kind')!r}")
        checks.append(c)
    if only and (set(only) - seen):
        # A filter that matches nothing must not read as a clean run.
        raise HarnessError(f"no such check id: {sorted(set(only) - seen)}")
    if not checks:
        raise HarnessError("no checks loaded")
    return checks


# ---------------------------------------------------------------- text tools


def short_repo(name: str) -> str:
    return name.rsplit("/", 1)[-1]


def repo_dir(family_dir: Path, repo: str) -> Path:
    d = family_dir / repo
    if not d.is_dir():
        raise HarnessError(f"family checkout missing: {d}")
    return d


def read_text(path: Path) -> str:
    if not path.is_file():
        raise HarnessError(f"file missing: {path}")
    return path.read_text(encoding="utf-8")


def heading_level(line: str) -> int:
    m = re.match(r"^(#{1,6})\s", line)
    return len(m.group(1)) if m else 0


def section_span(lines: list, heading_regex: str, where: str) -> tuple:
    """(start, end) line indexes of the section under the first heading
    matching heading_regex; end is exclusive. Raises when not found."""
    rx = re.compile(heading_regex)
    for i, line in enumerate(lines):
        if heading_level(line) and rx.search(line):
            lvl = heading_level(line)
            j = i + 1
            while j < len(lines):
                l2 = heading_level(lines[j])
                if l2 and l2 <= lvl:
                    break
                j += 1
            return i, j
    raise HarnessError(f"heading not found in {where}: /{heading_regex}/")


def select_lines(text: str, sections=None, exclude_sections=None, where="") -> list:
    """Return [(lineno, line)] restricted to the named sections (all lines
    when sections is empty) minus the excluded sections."""
    lines = text.split("\n")
    keep = [True] * len(lines)
    if sections:
        keep = [False] * len(lines)
        for h in sections:
            s, e = section_span(lines, h, where)
            for k in range(s, e):
                keep[k] = True
    for h in exclude_sections or []:
        s, e = section_span(lines, h, where)
        for k in range(s, e):
            keep[k] = False
    return [(i + 1, lines[i]) for i in range(len(lines)) if keep[i]]


def strip_cell(cell: str) -> str:
    c = cell.strip()
    c = re.sub(r"^\*\*(.*)\*\*$", r"\1", c)
    c = re.sub(r"^`(.*)`$", r"\1", c)
    return c.strip()


def parse_table(lines: list, start: int, end: int, where: str) -> tuple:
    """First markdown table inside lines[start:end] -> (headers, rows)."""
    i = start
    while i < end and not lines[i].lstrip().startswith("|"):
        i += 1
    if i >= end:
        raise HarnessError(f"no table in section at {where}")
    headers = [strip_cell(c) for c in lines[i].strip().strip("|").split("|")]
    rows = []
    i += 2  # skip the separator row
    while i < end and lines[i].lstrip().startswith("|"):
        cells = [strip_cell(c) for c in lines[i].strip().strip("|").split("|")]
        rows.append(dict(zip(headers, cells)))
        i += 1
    return headers, rows


def table_tuples(text: str, heading_regex: str, columns: list, where: str) -> set:
    lines = text.split("\n")
    s, e = section_span(lines, heading_regex, where)
    headers, rows = parse_table(lines, s, e, where)
    for col in columns:
        if col not in headers:
            raise HarnessError(f"column {col!r} not in table headers {headers} at {where}")
    return {tuple(r[c] for c in columns) for r in rows}


def json_path(obj, path: str):
    """Tiny path language: dotted keys, [] for every element, [n] for one.
    Returns a list of (display_path, value)."""
    out = [("", obj)]
    for token in re.findall(r"[^.\[\]]+|\[\]|\[\d+\]", path):
        nxt = []
        for disp, cur in out:
            if token == "[]":
                if isinstance(cur, list):
                    nxt.extend((f"{disp}[{k}]", v) for k, v in enumerate(cur))
            elif token.startswith("["):
                k = int(token[1:-1])
                if isinstance(cur, list) and k < len(cur):
                    nxt.append((f"{disp}[{k}]", cur[k]))
            else:
                if isinstance(cur, dict) and token in cur:
                    nxt.append((f"{disp}.{token}" if disp else token, cur[token]))
        out = nxt
    return out


def expand_files(rdir: Path, patterns: list, exclude: list | None = None,
                 may_be_empty: bool = False) -> list:
    """Files under rdir matching the globs. Zero files is a harness error: a
    forbidden-text check over no file would pass vacuously, and a renamed
    verifier must turn the gate red, not green."""
    files = []
    skip = set()
    for pat in exclude or []:
        skip.update(glob.glob(str(rdir / pat), recursive=True))
    for pat in patterns:
        hits = sorted(glob.glob(str(rdir / pat), recursive=True))
        files.extend(Path(h) for h in hits
                     if Path(h).is_file() and "/.git/" not in h and h not in skip)
    if not files and not may_be_empty:
        raise HarnessError(f"no files match {patterns} under {rdir.name} (a missing inspected file is never a pass)")
    return files


# ---------------------------------------------------------------- homes


def resolve_home(home: dict, family_dir: Path, require_marker: bool, findings: list) -> dict:
    """Locate the home section; report a missing marker as a finding when
    required. Returns {"text","lines","span","marker_present","block"}."""
    rdir = repo_dir(family_dir, home["repo"])
    path = rdir / home["file"]
    text = read_text(path)
    lines = text.split("\n")
    where = f"{home['repo']}/{home['file']}"
    s, e = section_span(lines, home["heading"], where)
    marker = MARKER.format(id=home["id"])
    present = any(marker in lines[k] for k in range(s, e))
    block = None
    if present:
        k = next(k for k in range(s, e) if marker in lines[k])
        while k < e and not lines[k].startswith("```json"):
            k += 1
        if k < e:
            j = k + 1
            body = []
            while j < e and not lines[j].startswith("```"):
                body.append(lines[j])
                j += 1
            try:
                block = json.loads("\n".join(body))
            except json.JSONDecodeError as exc:
                raise HarnessError(f"{where}: definition block after {marker} is not JSON: {exc}")
    if require_marker and not present:
        findings.append({
            "repo": home["repo"], "file": home["file"], "line": s + 1,
            "detail": f"home missing: no '{marker}' under the section heading",
        })
    return {"text": text, "lines": lines, "span": (s, e), "marker_present": present,
            "block": block, "where": where}


# ---------------------------------------------------------------- kinds


def kind_table_matches_registry(check, home, hinfo, family_dir, findings):
    cols = check["params"]["columns"]
    reg = table_tuples(hinfo["text"], home["heading"], cols, hinfo["where"])
    for ins in check["inspect"]:
        rdir = repo_dir(family_dir, ins["repo"])
        relation = ins.get("relation", "subset")
        if ins["type"] == "table":
            text = read_text(rdir / ins["file"])
            try:
                got = table_tuples(text, ins["heading"], ins.get("columns", cols),
                                   f"{ins['repo']}/{ins['file']}")
            except HarnessError:
                if ins.get("if_present"):
                    # No restatement under that heading (or none with these
                    # columns): the definition is not restated here, which is
                    # the target state. A present table still has to agree.
                    continue
                raise
            extra = sorted(got - reg)
            for t in extra:
                findings.append({"repo": ins["repo"], "file": ins["file"], "line": 0,
                                 "detail": f"table entry {t} is not in the home table"})
            if relation == "equal":
                for t in sorted(reg - got):
                    findings.append({"repo": ins["repo"], "file": ins["file"], "line": 0,
                                     "detail": f"home entry {t} is missing from this table"})
        elif ins["type"] == "regex-pairs":
            rx = re.compile(ins["regex"])
            for f in expand_files(rdir, ins["files"], ins.get("exclude_files"), ins.get("may_be_empty", False)):
                for ln, line in select_lines(read_text(f), ins.get("sections"),
                                             ins.get("exclude_sections"), str(f)):
                    for m in rx.finditer(line):
                        t = tuple(m.groups())
                        if t not in reg:
                            findings.append({"repo": ins["repo"], "file": str(f.relative_to(rdir)),
                                             "line": ln, "detail": f"{t} is not in the home table"})
        else:
            raise HarnessError(f"{check['id']}: unknown inspect type {ins['type']!r}")


def kind_regex_count(check, home, hinfo, family_dir, findings):
    for ins in check["inspect"]:
        rdir = repo_dir(family_dir, ins["repo"])
        rx = re.compile(ins["regex"], re.I if ins.get("ignorecase") else 0)
        hits = []
        for f in expand_files(rdir, ins["files"], ins.get("exclude_files"), ins.get("may_be_empty", False)):
            rel = str(f.relative_to(rdir))
            for ln, line in select_lines(read_text(f), ins.get("sections"),
                                         ins.get("exclude_sections"), rel):
                for m in rx.finditer(line):
                    hits.append((rel, ln, m.group(0)))
        if "expect" in ins and len(hits) != ins["expect"]:
            if hits:
                for rel, ln, s in hits:
                    findings.append({"repo": ins["repo"], "file": rel, "line": ln,
                                     "detail": f"{ins.get('why', 'forbidden text')}: {s!r}"})
            else:
                findings.append({"repo": ins["repo"], "file": ",".join(ins["files"]), "line": 0,
                                 "detail": f"expected {ins['expect']} match(es) of /{ins['regex']}/, found 0"})
        if "min" in ins and len(hits) < ins["min"]:
            findings.append({"repo": ins["repo"], "file": ",".join(ins["files"]), "line": 0,
                             "detail": f"{ins.get('why', 'required text absent')}: /{ins['regex']}/ "
                                       f"found {len(hits)} time(s), need {ins['min']}"})


def registry_set(reg: dict, hinfo: dict, home: dict, family_dir: Path) -> set:
    """Values of one column of the home table (default) or of another home."""
    src_home = home
    text = hinfo["text"]
    if reg.get("home"):
        src_home = load_homes()[reg["home"]]
        text = read_text(repo_dir(family_dir, src_home["repo"]) / src_home["file"])
    return {t[0] for t in table_tuples(text, src_home["heading"], [reg["column"]],
                                       f"{src_home['repo']}/{src_home['file']}")}


def kind_json_path_grammar(check, home, hinfo, family_dir, findings):
    p = check.get("params", {})
    value_rx = re.compile(p["value_regex"]) if p.get("value_regex") else None
    reg = p.get("registry")
    regset = registry_set(reg, hinfo, home, family_dir) if reg else None
    ex_rx = re.compile(reg["extract"]) if reg and reg.get("extract") else None
    exempt_rx = re.compile(reg["exempt_regex"]) if reg and reg.get("exempt_regex") else None
    block = hinfo.get("block") or {}
    for ins in check["inspect"]:
        rdir = repo_dir(family_dir, ins["repo"])
        all_values = []
        for f in expand_files(rdir, ins["files"], ins.get("exclude_files"), ins.get("may_be_empty", False)):
            rel = str(f.relative_to(rdir))
            values = []  # (line, value)
            if ins.get("path"):
                try:
                    obj = load_json(f)
                except json.JSONDecodeError as exc:
                    raise HarnessError(f"{rel}: not JSON: {exc}")
                for disp, v in json_path(obj, ins["path"]):
                    if ins.get("keys"):
                        values.extend((0, k) for k in (v.keys() if isinstance(v, dict) else []))
                    else:
                        values.append((0, v))
            elif ins.get("literal_regex"):
                lrx = re.compile(ins["literal_regex"])
                skip = re.compile(ins["exclude_regex"]) if ins.get("exclude_regex") else None
                split = re.compile(ins["split_regex"]) if ins.get("split_regex") else None
                for ln, line in select_lines(read_text(f), ins.get("sections"),
                                             ins.get("exclude_sections"), rel):
                    for m in lrx.finditer(line):
                        v = m.group(1) if m.groups() else m.group(0)
                        parts = [x for x in split.split(v) if x] if split else [v]
                        for part in parts:
                            if skip and skip.search(part):
                                continue
                            values.append((ln, part))
            else:
                raise HarnessError(f"{check['id']}: inspect needs path or literal_regex")
            all_values.extend(values)
            if ins.get("value_from_home"):
                want = block
                for k in ins["value_from_home"].split("."):
                    want = want.get(k) if isinstance(want, dict) else None
                exc = [e for e in block.get("exceptions", [])
                       if e.get("repo") == ins["repo"] and e.get("file") == rel
                       and e.get("path") == ins["path"]]
                for ln, v in values:
                    if want is None:
                        findings.append({"repo": ins["repo"], "file": rel, "line": ln,
                                         "detail": f"{ins['path']} = {v!r}; the home block does not state "
                                                   f"{ins['value_from_home']}"})
                    elif v != want and not any(e.get("value") == v for e in exc):
                        findings.append({"repo": ins["repo"], "file": rel, "line": ln,
                                         "detail": f"{ins['path']} = {v!r}, home says {want!r} and lists no exception"})
                continue
            for ln, v in values:
                if not isinstance(v, str):
                    findings.append({"repo": ins["repo"], "file": rel, "line": ln,
                                     "detail": f"non-string value {v!r}"})
                    continue
                if value_rx and not value_rx.search(v):
                    findings.append({"repo": ins["repo"], "file": rel, "line": ln,
                                     "detail": f"{v!r} does not match the home grammar"})
                    continue
                if regset is not None:
                    key = v
                    if ex_rx:
                        m = ex_rx.search(v)
                        key = m.group(1) if m else None
                    if exempt_rx and exempt_rx.search(v):
                        continue
                    if key not in regset:
                        findings.append({"repo": ins["repo"], "file": rel, "line": ln,
                                         "detail": f"{v!r}: {key!r} is not in the home registry"})
        if not all_values and ins.get("path") and not ins.get("may_be_empty"):
            raise HarnessError(f"{check['id']}: path {ins['path']!r} yields no value in any file of "
                               f"{ins['repo']} {ins['files']} (a path that reads nothing checks nothing)")


def kind_json_required_excludes(check, home, hinfo, family_dir, findings):
    for ins in check["inspect"]:
        rdir = repo_dir(family_dir, ins["repo"])
        rx = re.compile(ins["description_regex"])
        for f in expand_files(rdir, ins["files"], ins.get("exclude_files"), ins.get("may_be_empty", False)):
            rel = str(f.relative_to(rdir))
            obj = load_json(f)
            required = set(obj.get("required", []))
            for name, prop in obj.get("properties", {}).items():
                if isinstance(prop, dict) and rx.search(prop.get("description", "")) and name in required:
                    findings.append({"repo": ins["repo"], "file": rel, "line": 0,
                                     "detail": f"{name!r} is described as /{ins['description_regex']}/ "
                                               f"yet listed in required[]"})


def kind_enum_equal(check, home, hinfo, family_dir, findings):
    sets = []
    for src in check["params"]["sources"]:
        rdir = repo_dir(family_dir, src["repo"])
        f = rdir / src["file"]
        if src["type"] == "json":
            vals = [v for _, v in json_path(load_json(f), src["path"])]
            got = set(vals[0]) if vals and isinstance(vals[0], list) else set()
        elif src["type"] == "md-backticks":
            text = read_text(f)
            m = re.search(src["anchor_regex"], text)
            if not m:
                raise HarnessError(f"{src['repo']}/{src['file']}: anchor /{src['anchor_regex']}/ not found")
            stop = re.compile(src.get("stop_regex", r"[;.]"))
            tail = text[m.end():]
            sm = stop.search(tail)
            span = tail[: sm.start()] if sm else tail
            got = set(re.findall(r"`([^`]+)`", span))
        else:
            raise HarnessError(f"{check['id']}: unknown source type {src['type']!r}")
        sets.append((src, got))
    base_src, base = sets[0]
    for src, got in sets[1:]:
        if got != base:
            findings.append({"repo": src["repo"], "file": src["file"], "line": 0,
                             "detail": f"enum {sorted(got)} differs from {base_src['repo']}/{base_src['file']} "
                                       f"{sorted(base)}"})


def kind_citation_set_equal(check, home, hinfo, family_dir, findings):
    p = check["params"]
    s, e = hinfo["span"]
    para = None
    arx = re.compile(p["anchor_regex"])
    for k in range(s, e):
        if arx.search(hinfo["lines"][k]):
            para = hinfo["lines"][k]
            break
    if para is None:
        raise HarnessError(f"{hinfo['where']}: anchor /{p['anchor_regex']}/ not found in the home section")
    home_cites = set(re.findall(p["cite_regex"], para))
    for ins in check["inspect"]:
        rdir = repo_dir(family_dir, ins["repo"])
        obj = load_json(rdir / ins["file"])
        crx = re.compile(ins["cite_regex"])
        seen = set()
        for disp, item in json_path(obj, ins["path"]):
            cites = set(crx.findall(item if isinstance(item, str) else json.dumps(item)))
            if not cites:
                findings.append({"repo": ins["repo"], "file": ins["file"], "line": 0,
                                 "detail": f"{disp}: cites no specification section: {str(item)[:80]!r}"})
            seen |= cites
        for c in sorted(home_cites - seen):
            findings.append({"repo": ins["repo"], "file": ins["file"], "line": 0,
                             "detail": f"the home names section {c} as uncovered; no notCovered item cites it"})
        for c in sorted(seen - home_cites):
            findings.append({"repo": home["repo"], "file": home["file"], "line": s + 1,
                             "detail": f"notCovered cites section {c}; the home paragraph does not name it"})


RUNNERS = {
    "table-matches-registry": kind_table_matches_registry,
    "regex-count": kind_regex_count,
    "json-path-grammar": kind_json_path_grammar,
    "json-required-excludes": kind_json_required_excludes,
    "enum-equal": kind_enum_equal,
    "citation-set-equal": kind_citation_set_equal,
}


# ---------------------------------------------------------------- driver


def run_check(check: dict, homes: dict, family_dir: Path, caller: str | None) -> dict:
    home = homes.get(check["home"])
    if home is None:
        raise HarnessError(f"{check['id']}: home {check['home']!r} has no harness/homes file")
    findings: list = []
    inspected_repos = {home["repo"]} | {i["repo"] for i in check.get("inspect", [])}
    inspected_repos |= {s["repo"] for s in check.get("params", {}).get("sources", [])}
    result = {"id": check["id"], "title": check.get("title", ""), "sweep": check.get("sweep"),
              "kind": check["kind"], "home": f"{home['repo']}/{home['file']} {home['heading']}",
              "home_repo": home["repo"], "inspected_repos": sorted(inspected_repos),
              "in_scope": True, "caller_files": [], "status": "PASS", "findings": findings}
    try:
        hinfo = resolve_home(home, family_dir, check.get("require_marker", False), findings)
        RUNNERS[check["kind"]](check, home, hinfo, family_dir, findings)
    except HarnessError as exc:
        result["status"] = "ERROR"
        result["error"] = str(exc)
    if findings and result["status"] != "ERROR":
        result["status"] = "FAIL"
    # Scope: a check is the caller's when the caller owns the home, or when a
    # finding sits in a caller file. Being merely inspected, with every
    # finding elsewhere, is family drift for this caller, not its red.
    if caller is not None:
        caller_files = sorted({f["file"] for f in findings if f["repo"] == caller})
        result["caller_files"] = caller_files
        result["in_scope"] = caller == home["repo"] or bool(caller_files) or (
            result["status"] == "ERROR" and caller in inspected_repos)
    return result


def render_md(report: dict) -> str:
    out = ["# spec-drift report", "",
           f"caller: `{report['caller'] or '(family)'}`  scope: `{report['scope']}`  "
           f"verdict: **{report['verdict']}** (exit {report['exit']})", "",
           "| check | status | scope | home | findings |", "|---|---|---|---|---|"]
    for c in report["checks"]:
        scope = "caller" if c["in_scope"] else "family"
        out.append(f"| `{c['id']}` | {c['status']} | {scope} | {c['home']} | {len(c['findings'])} |")
    out.append("")
    for c in report["checks"]:
        if c["status"] == "PASS":
            continue
        out.append(f"## {c['id']} — {c['status']}" + ("" if c["in_scope"] else " (family drift, not this caller's)"))
        if c.get("title"):
            out.append(c["title"])
        if c["in_scope"] and c.get("caller_files"):
            out.append("In scope through caller files: " + ", ".join(f"`{f}`" for f in c["caller_files"]))
        elif c["in_scope"] and c.get("home_repo") and report.get("caller"):
            out.append(f"In scope because the caller owns the home ({c['home_repo']}).")
        if c.get("error"):
            out.append(f"harness error: {c['error']}")
        for f in c["findings"][:40]:
            loc = f"{f['repo']}/{f['file']}" + (f":{f['line']}" if f.get("line") else "")
            out.append(f"- `{loc}` {f['detail']}")
        if len(c["findings"]) > 40:
            out.append(f"- ... {len(c['findings']) - 40} more")
        if c.get("fix"):
            out.append(f"Fix: {c['fix']}")
        out.append("")
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--family-dir", required=True, help="directory holding one checkout per family repo")
    ap.add_argument("--scope", choices=("caller", "family"), default="caller")
    ap.add_argument("--caller", default=os.environ.get("GITHUB_REPOSITORY"),
                    help="owner/repo of the calling repository (default $GITHUB_REPOSITORY)")
    ap.add_argument("--check", action="append", help="run only this check id (repeatable)")
    ap.add_argument("--report-json", default="report.json")
    ap.add_argument("--report-md", default="report.md")
    ap.add_argument("--family-file", default=str(HERE / "family.json"))
    args = ap.parse_args(argv)

    family_dir = Path(args.family_dir).resolve()
    try:
        fam = load_family(Path(args.family_file))
        homes = load_homes()
        checks = load_checks(set(args.check) if args.check else None)
        for r in fam["repos"]:
            repo_dir(family_dir, r)
    except HarnessError as exc:
        print(f"spec-drift: harness error: {exc}", file=sys.stderr)
        return 2
    caller = short_repo(args.caller) if (args.scope == "caller" and args.caller) else None
    if args.scope == "caller" and caller is None:
        print("spec-drift: harness error: --scope caller needs --caller or $GITHUB_REPOSITORY", file=sys.stderr)
        return 2

    results = [run_check(c, homes, family_dir, caller) for c in checks]
    for c, r in zip(checks, results):
        r["fix"] = c.get("fix", "")
    errors = [r for r in results if r["status"] == "ERROR"]
    failing = [r for r in results if r["status"] == "FAIL" and r["in_scope"]]
    family_drift = [r for r in results if r["status"] == "FAIL" and not r["in_scope"]]
    if errors:
        code, verdict = 2, "ERROR"
    elif failing:
        code, verdict = 1, "DRIFT"
    else:
        code, verdict = 0, "CLEAN"
    report = {"caller": args.caller if caller else None, "scope": args.scope, "verdict": verdict,
              "exit": code, "checks": results,
              "summary": {"checks": len(results), "fail_in_scope": len(failing),
                          "fail_family": len(family_drift), "error": len(errors)}}
    Path(args.report_json).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    md = render_md(report)
    Path(args.report_md).write_text(md, encoding="utf-8")
    print(md)
    for r in errors:
        print(f"spec-drift: harness error in {r['id']}: {r['error']}", file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
