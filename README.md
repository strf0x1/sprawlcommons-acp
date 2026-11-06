# sprawlcommons-acp

The versioned Agent Client Protocol (ACP) extension contract between Deck and
Construct. It is the source of truth for the extension names, capability
negotiation, payloads and the compatibility window; neither implementation
repo owns it.

- [`SPEC.md`](SPEC.md) — normative names, negotiation and payloads.
- [`compatibility.md`](compatibility.md) — peer matrix, support table, sunset.
- [`schema/`](schema) — JSON Schema for every extension object.
- [`conformance/matrix.json`](conformance/matrix.json) — the machine-readable
  negotiation table both repositories test against.
- [`conformance/payloads.json`](conformance/payloads.json) — valid and invalid payload fixtures.
- Boundary observation schemas also cover the existing HTTP status/event feed.
- [`CHANGELOG.md`](CHANGELOG.md) — contracts are versioned; this says how.
- [Construct timed-grant handoff](.handoff/construct-timed-grants.md) — receiver
  adoption plan for contract 1.1.0.

`VERSION` is the contract version. Implementations pin a release and vendor the
machine-readable artifacts with a checksum; see
[`AGENTS.md`](AGENTS.md) for the change protocol.

This repository contains no implementation. Prose alone drifts, so a wire
change is not accepted until `matrix.json` and the schemas describe it.

Run `python3 -m pip install -r scripts/requirements.txt` then
`python3 scripts/check.py` to validate schemas, payload fixtures and negotiation.
