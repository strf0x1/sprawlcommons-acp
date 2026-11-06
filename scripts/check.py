#!/usr/bin/env python3
"""Check the contract's own artifacts agree with each other.

Uses the standard JSON Schema validator; install scripts/requirements.txt.
"""

import json
import pathlib
import sys

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = pathlib.Path(__file__).resolve().parent.parent
errors: list[str] = []


def load(path: pathlib.Path):
    try:
        return json.loads(path.read_text())
    except Exception as e:  # noqa: BLE001 - report, do not crash the gate
        errors.append(f"{path.relative_to(ROOT)}: {e}")
        return None


version = (ROOT / "VERSION").read_text().strip()
matrix = load(ROOT / "conformance/matrix.json")
schemas = {p: load(p) for p in sorted((ROOT / "schema").glob("*.json"))}

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
    spec = (ROOT / "SPEC.md").read_text()
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
        errors.append("boundary_grants constants disagree with contract 1.1")
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

if errors:
    print("FAILED")
    for e in errors:
        print(f"  {e}")
    sys.exit(1)
print(f"ok: contract {version}, {len(schemas)} schemas, {len(matrix['negotiation'])} negotiation cases, {len(payloads["cases"])} payload cases")
