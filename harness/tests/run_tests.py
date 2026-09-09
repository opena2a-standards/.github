#!/usr/bin/env python3
"""Self-test for the spec-drift harness.

Builds a small synthetic family in a temporary directory whose documents
satisfy every check (the CLEAN family: each home carries its marker and
block, every citer cites), asserts the family verdict is CLEAN, then applies
one planted drift per check and asserts the verdict is DRIFT on exactly that
check. The clean family also carries a `taskScopes` row and a task-scope
vocabulary token that would violate the capability grammar if the check read
them, proving the section exclusion.

python3 standard library only. Exit 0 when every assertion holds.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
HARNESS = HERE.parent / "spec_drift.py"

ATP = """# ATP

### 4.1 Trust Levels

<!-- opena2a-definition: trust-levels -->
| Level | Name | Meaning |
|-------|------|---------|
| 0 | Blocked | bad |
| 1 | Warning | concern |
| 2 | Listed | indexed |
| 3 | Scanned | assessed |
| 4 | Verified | consensus |

<!-- opena2a-definition: trust-score-scale -->
```json
{"scale": {"min": 0.0, "max": 1.0},
 "exceptions": [{"repo": "atx-spec", "file": "schemas/atx-credential-v1.1.schema.json",
                 "path": "properties.trustScore.maximum", "value": 100,
                 "reason": "ATX 1.1 wire encoding is frozen"},
                {"repo": "atx-conformance", "file": "schemas/vendor/atx-spec/atx-credential-v1.1.schema.json",
                 "path": "properties.trustScore.maximum", "value": 100,
                 "reason": "vendored copy of the frozen ATX 1.1 schema"}]}
```

### 4.2 Trust Proof Format

<!-- opena2a-definition: trust-verdict -->
`verdict` is one of `passed`, `warning`, `blocked`,
`listed`, `verified`, `unknown`; `trustScore` is 0.0-1.0.

### 4.4 Verification

4. **Signature:** every declared entry verifies (AAP Section 9.4).
5. **Semantic validation:**
   - `verdict` MUST be one of: `passed`, `warning`, `blocked`, `listed`, `verified`, `unknown`

#### 5.1.1 Entry type registry

<!-- opena2a-definition: transparency-entry-types -->
| Name | Byte | Data members | Since |
|------|------|--------------|-------|
| `trust_proof_issued` | 0x01 | agentDid | 1.0.0-rc1 |

### 10.2 Trust Proof Validity

<!-- opena2a-definition: clock-skew -->
Verifiers MUST tolerate at most 60 seconds of clock skew.

```json
{"maxSkewSeconds": 60}
```
"""

ATP_SCHEMA = {"properties": {"verdict": {"enum": ["passed", "warning", "blocked", "listed", "verified", "unknown"]}}}

AIP = """# AIP

### 4.1 Capability Format

<!-- opena2a-definition: capability-grammar -->
Capabilities are `namespace:action` strings.

### 4.2 Reserved Namespaces

<!-- opena2a-definition: capability-namespaces -->
| Namespace | Description | Risk Level |
|-----------|-------------|------------|
| `file` | Filesystem | Medium |
| `db` | Database | Medium |
| `api` | External API | Medium |
| `secrets` | Secret material | Critical |

### 5.1 Challenge-Response Protocol

3. **Freshness** — the verifier's clock is before `expiresAt`, within the bound of ATP Section 10.2.

### 6.2 Behavioral tier

Tiers are not trust levels; see ATP Section 4.1 for `trustLevel`.
"""

CORE = """# ATX

### 1.1 ATX schema

```json
{
  "agentDid": "did:opena2a:agent:acme/billing-agent",
  "capabilities": ["db:read", "api:call"],
  "declaredPurpose": {"capabilityJustification": {"db:read": ["billing:inquiry"]}}
}
```

### 1.3 Local verification algorithm

<!-- opena2a-definition: atx-verification-steps -->
2. Check expiresAt is in the future, within the skew bound of ATP Section 10.2.
7. Count distinct signer authorities. If trust level 3 or higher is required, the verifier MUST reject unless at least two distinct authorities signed.

#### 1.3a.2 JCS form

<!-- opena2a-definition: atx-tbs-exclusions -->
Excluded from the TBS: `id`; `transparencyLogIndex` (a dead field).

### 1.5 Declared purpose (optional)

#### 1.5.2 Sub-fields

| `taskScopes` | core | array of `namespace:objective` tokens |

#### 1.5.3 Vocabulary

The reserved task scope namespaces are `support`, `orchestrate`; example `support:triage`.

#### 1.5.4 Breadth is measured, not claimed

A "narrow" declaration that justifies `secrets:read` against trust level 2 (Listed).

## 12. Conformance

<!-- opena2a-definition: atx-conformance-coverage -->
**Coverage.** Requirements no fixture exercises include §1.3 step 7 and §7.

## 13. Security considerations

Every credential carries both families; see AAP Section 9.4.

## 14. Registry considerations

| Capability tokens | `namespace:action` grammar | Governed by AIP Section 4.2 and its generated registry. |
| Transparency-log entry types | registered name and byte | ATP Section 5.1.1 and its generated registry. |
"""

ATX_SCHEMA = {
    "$defs": {"did": {"type": "string", "pattern": "^did:[a-z0-9]+:[A-Za-z0-9._:@/-]+$"}},
    "required": ["id", "trustScore", "trustLevel"],
    "properties": {
        "transparencyLogIndex": {"type": "integer", "description": "Dead field, never populated"},
        "trustScore": {"type": "number", "minimum": 0, "maximum": 100},
        "trustLevel": {"type": "integer", "minimum": 0, "maximum": 4},
    },
}

FIXTURE = {"name": "baseline", "atx": {"agentDid": "did:opena2a:agent:agent_conformance_test_001",
                                        "capabilities": ["db:read", "file:read"],
                                        "declaredPurpose": {"capabilityJustification": {"db:read": ["support:triage"]}}}}

CONFORMANCE = {"notCovered": [
    {"item": "Distinct signer-authority count (ATX core.md section 1.3 step 7)", "reason": "no fixture"},
    {"item": "Cosignature requirements (ATX core.md section 7)", "reason": "no fixture"}]}

VERIFY_PY = "def verify(atx):\n    authorities = distinct_verified_authorities(atx)\n    return len(authorities) >= 2\n"
VERIFY_GO = "func verify(a *ATX) bool {\n\treturn len(distinctVerifiedAuthorities(a)) >= 2\n}\n"

AAP = """# AAP

### 4.2 Claims

| `trust_class` | MUST | `class:action` | The ATX capability (e.g. `db:read`). |

### 9.4 Multi-Signature Form

<!-- opena2a-definition: signature-family-gate -->
Every declared entry verifies; a token with an ML-DSA-65 entry MUST carry both families (`HYBRID_INCOMPLETE`).
"""

BROKER = "# Broker profile\n\nThe window (issuedAt/expiresAt with the clock skew bound of ATP Section 10.2).\n"

DID = """# did:opena2a

### 3.1 Syntax

<!-- opena2a-definition: did-syntax -->
```
opena2a-did = "did:opena2a:" resource-type ":" resource-id
```

### 3.1.1 Relationship to DID Core

The percent-encoded serialization `did:opena2a:mcp_server:%40scope%2Fname` is the strict equivalent.

### 3.2 Resource type registry

<!-- opena2a-definition: did-resource-types -->
| Resource type | Description |
|---------------|-------------|
| `registry` | A registry |
| `authority` | An authority |
| `agent` | An agent |
| `mcp_server` | An MCP server |

### 3.3 Identifier normalization

Compare after normalization; never normalize before signature verification.
"""

ABGS = """# ABGS

### 1.1 Purpose

### 1.2 Scope

<!-- opena2a-definition: governance-enforcement -->
- **Runtime enforcement**: the responsibility of runtime platforms. OASB-2 declares intent.
"""


def write(root: Path, rel: str, content) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, (dict, list)):
        p.write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8")
    else:
        p.write_text(content, encoding="utf-8")


def build_clean(root: Path) -> None:
    write(root, "agent-trust-protocol/ATP-SPEC.md", ATP)
    write(root, "agent-trust-protocol/schemas/trust-proof-v1.schema.json", ATP_SCHEMA)
    write(root, "agent-identity-protocol/AIP-SPEC.md", AIP)
    write(root, "atx-spec/core.md", CORE)
    write(root, "atx-spec/schemas/atx-credential-v1.1.schema.json", ATX_SCHEMA)
    write(root, "atx-conformance/schemas/vendor/atx-spec/atx-credential-v1.1.schema.json", ATX_SCHEMA)
    write(root, "atx-conformance/fixtures/baseline-valid.json", FIXTURE)
    write(root, "atx-conformance/conformance.json", CONFORMANCE)
    write(root, "atx-conformance/verifiers/python/verify.py", VERIFY_PY)
    write(root, "atx-conformance/verifiers/go/verify.go", VERIFY_GO)
    write(root, "agent-authorization-protocol/AAP-SPEC.md", AAP)
    write(root, "agent-authorization-protocol/AAP-BROKER-PROFILE.md", BROKER)
    write(root, "did-method-opena2a/did-method-opena2a.md", DID)
    write(root, "agent-governance-spec/specification.md", ABGS)
    for r in ("atp-conformance", "aip-conformance", "aap-conformance"):
        write(root, f"{r}/README.md", "# suite\n")


def mutate(root: Path, rel: str, old: str, new: str) -> None:
    p = root / rel
    s = p.read_text(encoding="utf-8")
    assert old in s, f"plant target not found in {rel}: {old!r}"
    p.write_text(s.replace(old, new, 1), encoding="utf-8")


def mutate_json(root: Path, rel: str, fn) -> None:
    p = root / rel
    obj = json.loads(p.read_text(encoding="utf-8"))
    fn(obj)
    p.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


# One planted drift per check: (check id, function applying the plant).
PLANTS = {
    "trust-level-names": lambda r: mutate(r, "atx-spec/core.md", "trust level 2 (Listed)", "trust level 2 (Limited)"),
    "trust-score-scale": lambda r: mutate(r, "agent-trust-protocol/ATP-SPEC.md",
                                          '"path": "properties.trustScore.maximum", "value": 100,\n                 "reason": "ATX 1.1',
                                          '"path": "properties.trustScore.maximum", "value": 1.0,\n                 "reason": "ATX 1.1'),
    "trust-verdict-enum": lambda r: mutate_json(r, "agent-trust-protocol/schemas/trust-proof-v1.schema.json",
                                                lambda o: o["properties"]["verdict"]["enum"].append("revoked")),
    "dead-field-not-required": lambda r: mutate_json(r, "atx-spec/schemas/atx-credential-v1.1.schema.json",
                                                     lambda o: o["required"].append("transparencyLogIndex")),
    "capability-grammar": lambda r: mutate_json(r, "atx-conformance/fixtures/baseline-valid.json",
                                                lambda o: o["atx"]["capabilities"].append("read:public")),
    "registry-home-terms": lambda r: mutate(r, "atx-spec/core.md", "Governed by AIP Section 4.2",
                                            "Governed with the capability registry in AIM"),
    "did-example-forms": lambda r: mutate(r, "atx-spec/core.md", "did:opena2a:agent:acme/billing-agent",
                                          "did:opena2a:a2a_agent:acme/billing-agent"),
    "notcovered-index-agrees-with-spec": lambda r: mutate_json(
        r, "atx-conformance/conformance.json",
        lambda o: o["notCovered"].append({"item": "Behavioral profile validation", "reason": "omitted"})),
    "forbidden-step7-proxy": lambda r: mutate(r, "atx-conformance/verifiers/python/verify.py",
                                              "len(authorities) >= 2", "not (len(issuer_chain) < 2)"),
    "hybrid-family-gate": lambda r: mutate(r, "agent-trust-protocol/ATP-SPEC.md",
                                           "every declared entry verifies (AAP Section 9.4)",
                                           "At least one signature MUST verify"),
    "governance-enforcement-claims": lambda r: mutate(r, "agent-governance-spec/specification.md",
                                                      "OASB-2 declares intent.",
                                                      "OASB-2 declares intent; the broker and FGA engine hold the agent to it."),
    "transparency-entry-types": lambda r: mutate(r, "atx-spec/core.md",
                                                 "ATP Section 5.1.1 and its generated registry.",
                                                 "issuance, revocation, build attestation. ATP-SPEC revision."),
    "clock-skew-bound": lambda r: mutate(r, "agent-trust-protocol/ATP-SPEC.md",
                                         "<!-- opena2a-definition: clock-skew -->\n", ""),
}


def run(family: Path, scope="family", caller=None) -> dict:
    out = family.parent / "report.json"
    cmd = [sys.executable, str(HARNESS), "--family-dir", str(family), "--scope", scope,
           "--report-json", str(out), "--report-md", str(family.parent / "report.md")]
    if caller:
        cmd += ["--caller", caller]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    rep = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
    rep["_rc"] = proc.returncode
    rep["_stderr"] = proc.stderr
    return rep


def main() -> int:
    failures = []
    check_ids = sorted(p.stem for p in (HERE.parent / "checks").glob("*.json"))
    missing = sorted(set(check_ids) - set(PLANTS))
    if missing:
        failures.append(f"checks without a planted-drift test: {missing}")
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / "clean"
        build_clean(base)
        rep = run(base)
        red = sorted(c["id"] for c in rep.get("checks", []) if c["status"] != "PASS")
        if rep["_rc"] != 0 or red:
            failures.append(f"clean family: rc={rep['_rc']} red={red} {rep.get('_stderr', '')[:300]}")
            for c in rep.get("checks", []):
                for f in c["findings"][:3]:
                    failures.append(f"   {c['id']}: {f['repo']}/{f['file']}:{f['line']} {f['detail']}")
        # caller scope: a caller outside every check's scope is CLEAN even on a drifted family
        drifted = Path(tmp) / "drifted"
        shutil.copytree(base, drifted)
        PLANTS["trust-level-names"](drifted)
        rep = run(drifted, scope="caller", caller="opena2a-standards/aap-conformance")
        if rep["_rc"] != 0:
            failures.append(f"caller scope: aap-conformance should be CLEAN on an ATX/AIP drift, rc={rep['_rc']}")
        rep = run(drifted, scope="caller", caller="opena2a-standards/atx-spec")
        if rep["_rc"] != 1:
            failures.append(f"caller scope: atx-spec should be DRIFT on its own prose, rc={rep['_rc']}")
        # one plant per check
        for cid, plant in PLANTS.items():
            fam = Path(tmp) / f"plant-{cid}"
            shutil.copytree(base, fam)
            plant(fam)
            rep = run(fam)
            red = sorted(c["id"] for c in rep.get("checks", []) if c["status"] != "PASS")
            if rep["_rc"] != 1 or red != [cid]:
                failures.append(f"plant {cid}: rc={rep['_rc']} red={red} {rep.get('_stderr', '')[:200]}")
        # harness error: an inspected file that vanished is exit 2, never a vacuous pass
        gone = Path(tmp) / "gone"
        shutil.copytree(base, gone)
        (gone / "atx-conformance/verifiers/python/verify.py").unlink()
        rep = run(gone)
        if rep["_rc"] != 2:
            failures.append(f"missing inspected file should be exit 2, got {rep['_rc']}")
        # harness error: a check filter that matches nothing is exit 2
        out = Path(tmp) / "nofilter.json"
        proc = subprocess.run([sys.executable, str(HARNESS), "--family-dir", str(base), "--scope", "family",
                               "--check", "no-such-check", "--report-json", str(out),
                               "--report-md", str(Path(tmp) / "nofilter.md")], capture_output=True, text=True)
        if proc.returncode != 2:
            failures.append(f"unknown --check id should be exit 2, got {proc.returncode}")
        # harness error: a JSON path that reads nothing is exit 2
        blind = Path(tmp) / "blind"
        shutil.copytree(base, blind)
        mutate_json(blind, "atx-conformance/fixtures/baseline-valid.json",
                    lambda o: o["atx"].__setitem__("caps", o["atx"].pop("capabilities")))
        rep = run(blind)
        if rep["_rc"] != 2:
            failures.append(f"a path reading nothing should be exit 2, got {rep['_rc']}")
        # harness error: a missing family checkout is exit 2, never a skip
        broken = Path(tmp) / "broken"
        shutil.copytree(base, broken)
        shutil.rmtree(broken / "did-method-opena2a")
        rep = run(broken)
        if rep["_rc"] != 2:
            failures.append(f"missing checkout should be exit 2, got {rep['_rc']}")
    if failures:
        print("spec-drift self-test: FAIL")
        for f in failures:
            print(" -", f)
        return 1
    print(f"spec-drift self-test: ok ({len(PLANTS)} planted drifts, caller scope, harness error)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
