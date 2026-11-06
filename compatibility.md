# Compatibility

Who may talk to whom, under contract 1.x. The normative negotiation cases are
in `conformance/matrix.json`; this page is the release view.

## Peer matrix

| Deck | Construct | Result |
|---|---|---|
| released (bare names) | released (bare names) | current behavior, no change |
| released | contract 1.x | Construct advertises both capability keys, accepts both boundary methods, sends `_construct/turn` and `_construct/event` because the client named nothing new; attach and late decisions keep working |
| contract 1.x | released | Deck prefers the current capability, falls back to the bare one, and sends the method the agent advertised; old Construct gets its bare names |
| contract 1.x | contract 1.x | only current names are used; both keys are advertised during the window |

## Support table

| Contract | ACP | Construct | Deck | Notes |
|---|---|---|---|---|
| 1.0.x | 1 | 0.4+ | current | transition window; bare names accepted |
| 1.1.0 | 1 | pending adoption | pending adoption | timed scope and absolute expiry metadata; names unchanged |
| 2.0.0 | 1, 2 rules declared | TBD | TBD | bare names removed |

Implementations declare the contract version they vendor (Construct:
`CONTRACT.lock`; Deck: its own lock once pinned). A peer that cannot read the
current names is not a supported pairing across major versions; within 1.x it
is.

1.0.1 corrects schemas to match the existing prose and implementations; it
changes no names, negotiation or supported peer pairing. Payload fixtures
ship with the schemas for offline conformance testing.

## Sunset

1. Both halves advertise the current and bare capability keys.
2. Both halves accept the current and bare inbound names.
3. Both halves send the name the peer advertised, else the bare name.
4. One release after both halves ship contract 1.x, contract 2.0.0 removes the
   bare names, `LEGACY_*` constants and dual advertisement.

Removal is a contract major and MUST land as its own coordinated wave.

## Timed grants (1.1.0)

| Sender | Reader | Observation behavior |
|---|---|---|
| 1.0.x | 1.1 | Non-timed payloads without expiry remain accepted; existing text/aliases are preserved |
| 1.1 timed metadata | 1.0.x | Scope is already a string; unknown expiry fields are ignored; old readers may omit expiry display |
| 1.1 | 1.1 | Timed records require an absolute grant deadline; receiver validates and presents it |

Every pairing retains host-only enforcement. An old reader's missing expiry
presentation cannot authorize or extend an operation. No capability or
method-name negotiation is added. Both boundary spellings remain accepted;
current-key preference and legacy fallback are unchanged. Unknown future
scope strings remain opaque informational labels, never authority.

A malformed timed record is rejected before seen-ID marking; a past deadline
is valid history and must not become a new timer. HTTP status/event metadata
uses the same deadline, while older nullable/absent HTTP scopes remain valid.
Do not backfill a missing timed deadline with receipt time plus five minutes.

Adoption: merge and tag `v1.1.0` here, then pin both implementations in the
same wave. A candidate implementation can use an immutable reviewed commit
with `scripts/acp-contract.sh update 1.1.0 <commit>` and remain draft until the
release exists. Do not hand-edit vendored schemas or drop either 1.x alias.
