# Construct: receive timed boundary grants (contract 1.1.0)

Implement the receiver side of `SPEC.md` §5.4: retain, validate and present
`scope: "timed"` and `expires_at_ms` on Deck boundary observations. Deck owns
grant decisions and enforcement. This task adds no permission decision,
renewal, automatic retry, or local authorization timer to Construct.

Grounding: reviewed Construct `origin/main` at
`9be0cd15a6d53c2367f90a919a95b454d8035bf8` (payload-conformance PR #181).
The inspected local checkout was clean but behind that commit. Read Construct's
`AGENTS.md`, preserve local work, and start from current main or an isolated
`codex/` branch. Recheck routine path changes before editing.

## R1 — Pin the shared contract

Read this repository's `SPEC.md` §4.4 and §5.3–5.4, `compatibility.md`,
`conformance/matrix.json`, `conformance/payloads.json`, and the four
`schema/boundary-*.schema.json` files. Those files are normative; this plan
does not replace them.

In Construct, use `scripts/acp-contract.sh update 1.1.0` after the contract is
merged and tagged `v1.1.0`. Before release, an immutable reviewed contract
commit may be used with `scripts/acp-contract.sh update 1.1.0 <commit>`; keep
that implementation PR draft. Never use a moving branch as the final pin.
This changes `CONTRACT.lock` and the vendored fixture directory under
`crates/construct/tests/fixtures/acp-contract/`. Do not edit vendored files.
The final release pin must match Deck's contract commit and checksum.

Check: `scripts/acp-contract.sh verify` and existing `acp_contract` tests.
Do not rename methods, tool names, capabilities or either 1.x alias.

## R2 — Validate every observation before state changes

Read `crates/construct/src/tools/boundary/{mod,client,note,status,wait}.rs`
and `crates/construct/src/acp/deck.rs`. Current `Entry`, `Outcome`, and
`Notice` accept scope but discard the deadline. `Server::boundary_notice`
decodes `Notice` before queuing. HTTP `Boundary::events` currently marks the
endpoint down on response decoding errors; a malformed record must instead
leave it usable for a later corrected response.

Add shared deadline validation for these three decoding paths (a small new
`tools/boundary/grant.rs` module is an optional design). Preserve existing
public fields where practical. Requirements:

- `timed` requires a deadline. If present for any scope, the deadline must be
  an integer-valued JSON number in `0..=9007199254740991` Unix milliseconds.
  Accept `42.0` and normalize it to 42, as the shared schema requires. Reject
  strings, null, booleans, fractional, negative and out-of-range values.
  A bare `Option<u64>` decoder alone does not implement these rules.
- Accept old records without deadlines, HTTP absent/null scope, unknown scope
  strings and unknown fields. Preserve the non-empty notice-ID validation
  introduced on main. Keep ACP scope's existing schema stricter than HTTP's
  nullable scope; do not accidentally broaden the ACP decoder.
- Validate before advancing event cursors, marking approval IDs seen, or
  queuing notices. Reject an invalid record/response as an error, or ignore
  invalid events without losing corrected records. Do not permanently mark
  a reachable transport down because a record was malformed. Preserve actual
  transport-failure behavior.
- Past deadlines are valid history. Keep the host outcome and exact deadline;
  arrival, polling and reconnect never create a fresh five-minute interval.

Check: extend `crates/construct-dev/tests/acp_payloads.rs` so the actual
`Notice` decoder matches every notice fixture, including integral numbers.
Exercise HTTP status and both array/wrapped event decoders with the shared
positive/negative fixtures, using a small unit-test seam if necessary.
Prove a malformed record followed by a corrected record with the same ID is
delivered, and malformed HTTP data followed by a valid response recovers.

## R3 — Show the same deadline on every model-facing surface

In `note.rs`, extend `describe`, `status_text`, and `notifications` so tool
notes, wait/status answers and late notices retain scope and absolute expiry.
An unambiguous rendering is `expires_at_ms=1800000300000 (Unix ms)`; do not
display an arrival-relative countdown or claim access is currently usable.
Keep existing text byte-identical when no deadline is present. Unknown scopes
remain informational. Existing policy/bypass guidance stays intact.

In `status.rs` and `wait.rs`, retain `approval` and `outcome` in structured
results, add `scope` when supplied and `expires_at_ms` when supplied. Omit
absent new fields. Do not change the wait timeout into a grant deadline or
alter cancellation/withdrawal behavior. Deadline display must not bypass
the existing approval-ID deduplication across HTTP and both ACP aliases.

Check: extend `crates/construct-dev/tests/deck.rs` and its
`common/boundary.rs` HTTP helper. Script real model/tool exchanges to verify
the exact host deadline in wait/status structured data and model-visible
text, appended tool notes and late notifications. Cover a past deadline,
both ACP spellings with one delivery, HTTP resolution suppressing a later
duplicate, an unknown scope, and unchanged legacy text. Assert no extra
blocked-command invocation happens merely because a notice arrives. Unit
tests for the shared formatter/decoder may live in the corresponding module.

## R4 — Verify and report

Run in Construct:

```sh
scripts/acp-contract.sh verify
cargo test -p construct
cargo test -p construct-dev --test it acp_payloads::
cargo test -p construct-dev --test it deck::
cargo run -q -p construct-dev -- check --quick
```

The focused suites prove wire decoding and observable scripted behavior;
the quick gate supplies the repository's formatting/lint/structure checks.
No live provider or paid model is needed. Cite `contract@1.1.0 §5.4` in the
implementation PR. Report R1–R4 separately, commands actually run and their
outcomes, and whether the pin remains a draft candidate or is release-final.

## Guardrails

Read the named files before editing; do not survey unrelated areas or read
dependency sources. This contract repository and the named vendored fixtures
are the explicit exceptions to that reading boundary. Change only the listed
files plus required module declarations/test seams; explain any expansion.
No unrelated refactors, Deck changes, dependency changes, tool-description
changes or golden re-recording. Preserve unrelated work. Report unrelated
failures without fixing or weakening them. Keep test homes/scratch files
outside the repository or under ignored `target/`. This plan grants no
permission to commit, push, merge or deploy; follow the user's instructions.
