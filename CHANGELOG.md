# Changelog

Contract versions are semver (see `SPEC.md` §2).

## 1.1.0 — candidate

Additive timed-grant observation metadata; no new method or capability.

- Define `scope: "timed"` with an absolute `expires_at_ms` Unix-ms deadline.
- Fix the five-minute host interval at decision time; prohibit renewal by
  traffic, reconnect, polling or agent requests. Specify exclusive expiry.
- Share metadata across ACP notices and existing boundary HTTP status/events.
- Add schemas, positive/negative fixtures and deadline boundary cases.
- Preserve 1.x names, aliases, legacy non-timed records, unknown fields and
  approval-ID deduplication. Notifications still grant no authority.

## 1.0.1 — 2026-11-04

Schema and fixture corrections; no wire or negotiation change.

- Accept the documented boundary `id` alias, with a non-empty ID.
- Enforce the existing dual-key snapshot and idle-only stop-reason rules.
- Add positive and negative payload fixtures for every schema, validated in CI.

## 1.0.0 — 2026-11-03

Initial contract, extracted from Construct ADR 0038 and Deck ADR 0005 after
the rename landed in both implementations.

- Reverse-DNS namespace `com.sprawlcommons` for Construct and Deck extension
  names.
- Capability negotiation for the lossless event channel and turn method.
- Boundary notification and its method selection.
- Child `start` payload and the dual-key load snapshot.
- Bare names remain accepted and advertised until contract 2.0.0.
