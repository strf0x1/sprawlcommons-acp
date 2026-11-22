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
| 1.2.0 | 1 | pending adoption | pending adoption | GitHub operation API (§11); ACP names unchanged |
| 1.3.0 | 1 | pending adoption | pending adoption | idempotent prompts (§12); ACP names unchanged |
| 1.4.0 | 1 | pending adoption | pending adoption | coordinator task control (§13); ACP names unchanged |
| 1.5.0 | 1 | pending adoption | pending adoption | coordinator project defaults (§13.3); ACP names unchanged |
| 1.6.0 | 1 | pending adoption | pending adoption | coordinator integration workers (§13.7); ACP names unchanged |
| 1.7.0 | 1 | pending adoption | pending adoption | optional local worktree facts (§13.4); ACP names unchanged |
| 1.8.0 | 1 | pending adoption | pending adoption | optional permission observations and same-turn wait wake (§13.4); no answer operation |
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

## GitHub operations (1.2.0)

| Deck (server) | Construct (client) | Result |
|---|---|---|
| ≤ 1.1 | 1.2 | No `DECK_GITHUB_URL` in the guest; the client reports that it cannot publish from this sandbox and does not fall back to `git push` or `gh` |
| 1.2 | ≤ 1.1 | No `github_operations` capability; Deck tells the user this agent cannot publish from a sandbox |
| 1.2 | 1.2 | `refs` for the destination, then `publish` / `create_pr` / `update_pr` / `review` |

Local (non-VM) tasks have no gateway and no `DECK_GITHUB_URL`; Construct's
host-credential path is outside this contract. The wire is new, so no gateway
release before 1.2.0 needs compatibility: the server adopts the closed
requests, the uniform refusal body and `deck_not_permitted` in the same wave
as the client.

## Idempotent prompts (1.3.0)

| Client | Agent | Behavior |
|---|---|---|
| 1.2 | 1.3 | No key is sent; prompts behave as before |
| 1.3 | 1.2 | No `idempotentPrompts` is advertised, so no key is sent; a prompt whose response was lost is the user's to resend, never the client's on its own |
| 1.3 | 1.3 | A resent prompt with its key starts no second turn and is answered with the original's outcome |

The key is v2's `PromptRequest.idempotencyKey` under a v1 `_meta` key. Contract
2.0 moves it to the top-level parameter without changing what it means.

## Coordinator task control (1.4.0)

| Deck (server) | Construct (client) | Result |
|---|---|---|
| ≤ 1.3 | 1.4 | No `DECK_CONTROL_URL`; the client offers no control tool |
| 1.4 | ≤ 1.3 | The variables are ignored; the coordinator cannot control tasks |
| 1.4 | 1.4, VM coordinator | Guest loopback, no `DECK_CONTROL_TOKEN`, no header |
| 1.4 | 1.4, local coordinator | Host loopback with `DECK_CONTROL_TOKEN`; every request carries `Authorization: Bearer`, or is 401 |

The wire is new, so no gateway release before 1.4.0 needs compatibility:
Deck (deck#152) and Construct (construct#222) pin 1.4.0 in the same wave.
No `initialize` field is added, so every ACP pairing above is unchanged.

## Coordinator project defaults (1.5.0)

| Deck (server) | Construct (client) | Result |
|---|---|---|
| 1.4 | 1.5 | A `create` without `project` is `deck_control_bad_request`; `tasks` has no `projects`. A client that may meet a 1.4 server sends `project` (it is in every summary) |
| 1.5 | 1.4 | The client always sends `project` and ignores `projects`; nothing changes |
| 1.5 | 1.5 | The client omits `project` for a one-project coordinator and learns the set from `tasks` |

Deck and Construct pin 1.5.0 in the same wave, so the first row only occurs
across an unpaired upgrade.

## Coordinator integration workers (1.6.0)

| Deck (server) | Construct (client) | Result |
|---|---|---|
| 1.5 | 1.6 | Deck returns `deck_control_refused` for `integrate`. Construct reports the refusal. |
| 1.6 | 1.5 | Existing operations work. Construct ignores `integration` in task summaries. |
| 1.6 | 1.6 | Construct requests integration and reads its pins and waiting reason through the normal task operations. |

## Coordinator permission observations (1.8.0)

| Deck server | Construct client | Behavior |
|---|---|---|
| 1.7 or earlier | 1.8 | Missing `permissions` means unavailable; existing summaries still work. |
| 1.8 | 1.7 or earlier | Unknown optional fields are ignored. Existing operations still work. |
| 1.8 | 1.8 | Pending titles and observed verdicts appear in task, tasks and wait output. |

No capability, request field or operation is added. The coordinator cannot
answer a question. Unknown future kinds and verdicts are informational.
Implementations may pin an immutable candidate commit and remain draft
until `v1.8.0` is merged and tagged, then refresh both pins in the same wave.
