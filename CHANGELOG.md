# Changelog

Contract versions are semver (see `SPEC.md` §2).

## 1.5.0 — unreleased

Additive: a coordinator no longer has to find its project key (SPEC.md
§13.3; deck#198). Found in the first live coordinator run, where the model
guessed project names, was refused, and stopped until the user typed the key.

- `create`'s `project` is optional. Omitted, the server uses the
  coordinator's project when its set has exactly one, and otherwise refuses
  with `deck_control_bad_request` naming the set's ids.
- `tasks` replies carry `projects`, the coordinator's whole project set as
  `{ id, name }`, even when no task exists yet.
- A `deck_control_scope` message names the project ids in the set.
- Schemas: `control-create-request` no longer requires `project`;
  `control-tasks-response` requires `projects`. Payload cases and
  `create-default-project-{vm,local}` exchanges; `tasks` exchanges carry
  `projects`.

## 1.4.0 — 2026-11-17

Additive: the coordinator task-control API between a coordinator task and
Deck's host gateway (SPEC.md §13; Deck ADR 0011 §4). No ACP name,
negotiation, capability or existing payload changes.

- `POST /control` with one JSON operation of at most 32768 bytes, from the
  closed set `tasks`, `task`, `create`, `prompt`, `wait`, `stop`; requests are
  closed (unknown fields refused), replies are open.
- Discovery through `DECK_CONTROL_URL` (a loopback `http://host:port`), set
  only for a coordinator; no `initialize` capability.
- Optional per-task bearer token `DECK_CONTROL_TOKEN`, required by the host
  whenever the address is on host loopback (local coordinators): a missing,
  wrong or other-scheme `Authorization` header is 401
  `deck_control_unauthorized`, checked before the body. Without the variable
  (VM coordinators) no header is sent and any header is ignored. The token
  keeps other host processes off the surface; it does not confine the agent.
- Task summary: id, project, title (≤ 80), lifecycle state, turn, attention,
  pending approvals, publication, pull request, `created_by`, last assistant
  message (≤ 2048 bytes). `tasks` returns at most 200 with `truncated`.
- `wait` is a long poll with a required `wait_ms` of 0 to 300000; it wakes on
  a terminal lifecycle, an idle turn after `after_turn`, or new attention. A
  timeout is `200` with `timed_out: true` and the current summary.
- One refusal body (`control-error`) for every non-2xx reply, with the
  eight-code table: `deck_control_bad_request` (400/404/405/411/413),
  `deck_control_unauthorized` (401), `deck_control_scope`, `deck_control_cap`,
  `deck_control_refused` (403), `deck_control_unknown` (404),
  `deck_control_busy` (409), `deck_control_unavailable` (503), each with a
  fixed `retryable`. A task outside scope is `deck_control_unknown`.
- Fourteen `control-*` schemas, payload fixtures, and `matrix.json` `control`
  with 45 request exchanges (with and without the bearer header) that
  `scripts/check.py` replays through the gateway's own rules.

## 1.3.0 — 2026-11-17

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
