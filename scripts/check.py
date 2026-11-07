#!/usr/bin/env python3
"""Check the contract's own artifacts agree with each other.

Uses the standard JSON Schema validator; install scripts/requirements.txt.
"""

import base64
import json
import pathlib
import sys

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = pathlib.Path(__file__).resolve().parent.parent
errors: list[str] = []


def bundle_header(data: bytes):
    """The refs and prerequisites of a git bundle v2 header, or None."""
    if not data.startswith(b"# v2 git bundle\n"):
        return None
    refs, prerequisites = [], []
    rest = data[len(b"# v2 git bundle\n"):]
    while True:
        end = rest.find(b"\n")
        if end < 0:
            return None
        line, rest = rest[:end].decode("utf-8", "replace"), rest[end + 1:]
        if not line:
            return refs, prerequisites
        if line.startswith("-"):
            prerequisites.append(line[1:].split(" ", 1)[0])
        else:
            sha, _, name = line.partition(" ")
            refs.append((name, sha))


def frame_outcome(body: bytes, publish_schema, limits):
    """What a server concludes from one publish body: (status, parsed)."""
    try:
        head, end = json.JSONDecoder().raw_decode(body.decode("latin-1"))
    except ValueError:
        return 400, None
    if not publish_schema.is_valid(head):
        return 400, None
    rest = body[end:]
    if len(rest) < 4:
        return 411, None
    length = int.from_bytes(rest[:4], "big")
    if length > limits["bundle_bytes"]:
        return 413, None
    bundle = rest[4:]
    if len(bundle) != length:
        return 400, None
    header = bundle_header(bundle)
    if header is None:
        return 400, None
    refs, prerequisites = header
    if len(refs) != 1 or refs[0][0] != "refs/heads/" + head["branch"]:
        return 400, None
    return 200, {"branch": head["branch"], "ref": refs[0][0], "commit": refs[0][1], "prerequisites": prerequisites}


def check_github(github, schemas, validators, spec):
    if not github:
        errors.append("matrix.github is missing")
        return
    cap = github["capability"]
    if (cap["meta_key"], cap["field"], cap["version"], cap["legacy_key"]) != (
            "com.sprawlcommons/deck", "github_operations", 1, False):
        errors.append("github capability disagrees with contract 1.2")
    ops = github["operations"]
    if [op["operation"] for op in ops] != ["publish", "refs", "create_pr", "update_pr", "review"]:
        errors.append("the GitHub operation set is closed at five operations")
    if len({op["path"] for op in ops}) != len(ops):
        errors.append("every GitHub operation needs its own path")
    for op in ops:
        for key in ("request", "response"):
            if op[key] not in validators:
                errors.append(f"{op['operation']}: {op[key]} is not a schema")
        for term in (op["operation"], op["path"], op[key].removesuffix(".schema.json")):
            if f"`{term}`" not in spec:
                errors.append(f"SPEC.md §11 never names `{term}`")
        request = next((s for p, s in schemas.items() if p.name == op["request"]), None)
        if request and request.get("properties", {}).get("operation", {}).get("const") != op["operation"]:
            errors.append(f"{op['request']} does not pin operation {op['operation']}")
        if request and request.get("additionalProperties") is not False:
            errors.append(f"{op['request']} must be closed")
    codes = [r["code"] for r in github["refusals"]]
    error_schema = next((s for p, s in schemas.items() if p.name == "github-error.schema.json"), None)
    if error_schema and error_schema["properties"]["error"]["properties"]["code"]["enum"] != codes:
        errors.append("github-error code enum disagrees with matrix.github.refusals")
    for code in codes:
        if f"`{code}`" not in spec:
            errors.append(f"SPEC.md §11.5 never names `{code}`")
    for name in github["refused_by_name"]:
        if name in codes or f"`{name}`" not in spec:
            errors.append(f"SPEC.md §11.2 does not refuse `{name}` by name")
    if f"`{github['environment']}`" not in spec:
        errors.append("SPEC.md §11.1 never names the discovery variable")
    publish = validators.get("github-publish-request.schema.json")
    seen = set()
    for case in github["framing_cases"]:
        seen.add(case["case"])
        status, parsed = frame_outcome(base64.b64decode(case["body_base64"]), publish, github["limits"])
        want = case["expect"]
        if want["valid"]:
            got = {k: want[k] for k in ("branch", "ref", "commit", "prerequisites")}
            if status != 200 or parsed != got:
                errors.append(f"framing {case['case']}: expected {got}, got {status} {parsed}")
        elif status != want["status"]:
            errors.append(f"framing {case['case']}: expected {want['status']}, got {status}")
    if not {"full-bundle", "incremental-bundle", "two-refs", "no-bundle",
            "declared-length-over-limit"} <= seen:
        errors.append("framing cases must cover full, incremental, extra refs, missing and oversize bundles")


def load(path: pathlib.Path):
    try:
        return json.loads(path.read_text())
    except Exception as e:  # noqa: BLE001 - report, do not crash the gate
        errors.append(f"{path.relative_to(ROOT)}: {e}")
        return None


version = (ROOT / "VERSION").read_text().strip()
matrix = load(ROOT / "conformance/matrix.json")
schemas = {p: load(p) for p in sorted((ROOT / "schema").glob("*.json"))}
spec = (ROOT / "SPEC.md").read_text()

if matrix:
    names = matrix["names"]
    if matrix["contract"] != version:
        errors.append(f"matrix.contract {matrix['contract']} != VERSION {version}")
    for case in matrix["negotiation"]:
        for field in ("event_method", "turn_method"):
            if case["expect"][field] not in names.values():
                errors.append(f"{case['case']}: {field} {case['expect'][field]} is not in names")
    accepts = matrix["accepts"]
    expected = {
        "boundary_methods": [names["boundary_method"], names["boundary_method_legacy"]],
        "start_meta_keys": [names["construct_meta"], names["construct_meta_legacy"]],
        "load_snapshot_keys": [names["construct_meta"], names["construct_meta_legacy"]],
    }
    for key, want in expected.items():
        if accepts.get(key) != want:
            errors.append(f"accepts.{key} {accepts.get(key)} != {want}")
    for name in names.values():
        if name not in spec:
            errors.append(f"SPEC.md never names {name}")
    for case in matrix["negotiation"]:
        if case["case"] not in spec:
            errors.append(f"SPEC.md does not describe negotiation case {case['case']}")

    grant = matrix.get("boundary_grants", {})
    if (grant.get("timed_scope"), grant.get("deadline_field"), grant.get("duration_ms"),
            grant.get("deadline_exclusive"), grant.get("new_capability_required")) != (
            "timed", "expires_at_ms", 300000, True, False):
        errors.append("boundary_grants constants disagree with contract 1.1+")
    for case in grant.get("deadline_cases", []):
        if case["expires_at_ms"] != case["decision_at_ms"] + grant["duration_ms"]:
            errors.append(f"{case['case']}: observation must not renew the grant")
        if case["elapsed"] != (case["observed_at_ms"] >= case["expires_at_ms"]):
            errors.append(f"{case['case']}: expiry is exclusive")
    if {case["case"] for case in grant.get("deadline_cases", [])} != {
            "before-deadline", "at-exclusive-deadline", "late-notice-does-not-renew"}:
        errors.append("boundary_grants must cover admission, exclusive expiry and delayed delivery")
    for term in ("expires_at_ms", 'scope: "timed"', "300000"):
        if term not in spec:
            errors.append(f"SPEC.md never defines {term}")

for path, schema in schemas.items():
    if schema and "$schema" not in schema:
        errors.append(f"{path.relative_to(ROOT)} has no $schema")

payloads = load(ROOT / "conformance/payloads.json")
if payloads:
    if payloads["contract"] != version:
        errors.append("payloads.contract disagrees with VERSION")
    registry = Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema))
        for schema in schemas.values() if schema
    )
    validators = {}
    for path, schema in schemas.items():
        Draft202012Validator.check_schema(schema)
        validators[path.name] = Draft202012Validator(schema, registry=registry)
    covered = set()
    names = set()
    for case in payloads["cases"]:
        if case["case"] in names:
            errors.append(f"duplicate payload case {case['case']}")
        names.add(case["case"])
        covered.add(case["schema"])
        got = validators[case["schema"]].is_valid(case["payload"])
        if got != case["valid"]:
            errors.append(f"{case['case']}: expected valid={case['valid']}, got {got}")
    if covered != set(validators):
        errors.append("payload fixtures must cover every schema")

if matrix and payloads:
    check_github(matrix.get("github"), schemas, validators, spec)

if errors:
    print("FAILED")
    for e in errors:
        print(f"  {e}")
    sys.exit(1)
print(f"ok: contract {version}, {len(schemas)} schemas, {len(matrix['negotiation'])} negotiation cases, "
      f"{len(payloads['cases'])} payload cases, {len(matrix['github']['framing_cases'])} framing cases")
