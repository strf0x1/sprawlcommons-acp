# Changelog

Contract versions are semver (see `SPEC.md` §2).

## 1.0.0 — 2026-11-03

Initial contract, extracted from Construct ADR 0038 and Deck ADR 0005 after
the rename landed in both implementations.

- Reverse-DNS namespace `com.sprawlcommons` for Construct and Deck extension
  names.
- Capability negotiation for the lossless event channel and turn method.
- Boundary notification and its method selection.
- Child `start` payload and the dual-key load snapshot.
- Bare names remain accepted and advertised until contract 2.0.0.
