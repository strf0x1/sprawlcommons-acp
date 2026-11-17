# Changelog

Contract versions are semver (see `SPEC.md` §2).

## 1.3.0 — candidate

Additive: idempotent prompts (SPEC.md §12). A client can resend a
`session/prompt` whose response it never got without the prompt running
twice. Mirrors ACP v2's `PromptRequest.idempotencyKey` (name, length, errors,
reused-key rules) on ACP v1, whose response is the turn's stop reason. No ACP
name, negotiation or existing payload changes.

- Agent capability `com.sprawlcommons/construct.idempotentPrompts` (boolean),
  current key only.
- `session/prompt` `_meta["com.sprawlcommons/construct"].idempotencyKey`: an
  opaque string of 1 to 255 characters, scoped to the session; `null` or absent
  means no key; any other value is refused with `-32602`.
- The agent records the key with the prompt before the turn starts and keeps
  it as long as the session can be loaded. A recorded key starts no turn: the
  request is answered with the queued or running turn's outcome, the ended
  turn's stop reason, or `cancelled` for a turn cut off by a restart.
- A recorded key with a different prompt is answered as a retry or refused
  with `-32602` and `data.reason = "idempotency_key_conflict"`; the key stays
  with the first prompt. Keys are never echoed on the wire.
- Schemas `prompt-meta` and `idempotency-conflict`, fixtures, and the
  `idempotent_prompts` table in `matrix.json` that both implementations
  iterate.

## 1.2.0 — candidate

Additive: the GitHub operation API between a sandboxed agent and Deck's host
gateway (SPEC.md §11; Deck ADR 0007, ADR 0008). No ACP name, negotiation or
existing payload changes.

- Agent capability `com.sprawlcommons/deck.github_operations` (integer, `1`),
  current key only; discovery through `DECK_GITHUB_URL`.
- Request and success schemas for `publish`, `refs`, `create_pr`,
  `update_pr`, `review`; requests are closed (unknown fields refused).
- `refs` reports the host policy: `repository`, `base`, `task_branch` (before
  the branch exists) and `writable`.
- Publish framing (JSON head, u32 big-endian length, one-ref bundle v2, 64 KiB
  and 16 MiB bounds) with eight base64 body fixtures in `matrix.json`.
- Optional guest-supplied `summary { subject, count }` on `publish`, for
  approval cards only.
- `review` reports `merged`; `update_pr` sets `body` by presence (no
  `empty_body`).
- One refusal body for every non-2xx reply, with the 14-code table, status,
  `retryable`, `current` and `approval_id` rules; `deck_not_permitted` for
  operations outside the set.

## 1.1.0 — 2026-11-06

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
