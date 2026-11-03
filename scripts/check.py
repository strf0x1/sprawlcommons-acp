#!/usr/bin/env python3
"""Check the contract's own artifacts agree with each other.

No third-party dependencies: this runs in CI and must stay boring.
"""

import json
import pathlib
import sys

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

for path, schema in schemas.items():
    if schema and "$schema" not in schema:
        errors.append(f"{path.relative_to(ROOT)} has no $schema")

if errors:
    print("FAILED")
    for e in errors:
        print(f"  {e}")
    sys.exit(1)
print(f"ok: contract {version}, {len(schemas)} schemas, {len(matrix['negotiation'])} negotiation cases")
