# SprawlCommons ACP extension contract

Status: normative. Contract version `1.1.0` (see `VERSION`). Applies to ACP
protocol version 1.

The keywords MUST, MUST NOT, SHOULD and MAY are as in RFC 2119.

## 1. Scope

ACP (agentclientprotocol.com) is the wire between Deck and Construct in both
directions:

- Deck is the **client** (it runs a session and sends `session/*` requests).
- Construct is the **agent** for a user session, and the **client** when it
delegates to a child.

ACP only fixes the standard vocabulary. This contract fixes the extensions the
two projects share, and the compatibility window while released peers still
speak the old names.

ACP reserves `_`-prefixed methods for extensions and, in v2, reserves
unprefixed `_meta` keys. Extension `_meta` keys therefore use a reverse-DNS
namespace: `com.sprawlcommons/<product>`, and extension methods are
`_com.sprawlcommons/<product>/<name>`.

## 2. Versioning

Two axes are independent and MUST both be declared by an implementation:

| Axis | This release | Meaning |
|---|---|---|
| `acp` | `1` | The ACP protocol version the peer speaks |
| `contract` | `1.1.0` | This document and its schemas |

Contract versions are semver:

- **patch** — prose, schema or fixture correction; no wire change.
- **minor** — an additive capability, method or field that an older peer can
  ignore.
- **major** — a rename or removal, or a change to existing payload meaning.

## 3. Names

| Use | Name | Status |
|---|---|---|
| Construct `_meta` key | `com.sprawlcommons/construct` | current |
| Construct `_meta` key (legacy) | `construct` | accepted until contract 2.0 |
| Deck `_meta` key | `com.sprawlcommons/deck` | current |
| Deck `_meta` key (legacy) | `deck` | accepted until contract 2.0 |
| Lossless event notification | `_com.sprawlcommons/construct/event` | current |
| Lossless event notification (legacy) | `_construct/event` | accepted until contract 2.0 |
| Turn state notification | `_com.sprawlcommons/construct/turn` | current |
| Turn state notification (legacy) | `_construct/turn` | accepted until contract 2.0 |
| Boundary notification | `_com.sprawlcommons/deck/boundary` | current |
| Boundary notification (legacy) | `_deck/boundary` | accepted until contract 2.0 |

The constants above are normative and also live in
`conformance/matrix.json` under `names`.

## 4. Capability negotiation

Capabilities are exchanged once per attachment, in `initialize`.

### 4.1 Construct as agent (initialize response)

The agent MUST advertise `agentCapabilities._meta`:

```json
{
  "com.sprawlcommons/construct": { "events": true, "liveAttach": true },
  "construct":                  { "events": true, "liveAttach": true },
  "com.sprawlcommons/deck":     { "boundary": true },
  "deck":                       { "boundary": true }
}
```

- `events` means the lossless event channel exists and SHOULD be true.
- `liveAttach` is user-mode only; a delegated child MUST NOT advertise it.
- `boundary` is advertised only when this process has a Deck boundary
  endpoint. Deck MUST NOT send a boundary notification to an agent that did
  not advertise it under either key.

### 4.2 Construct as client (initialize request)

When Construct delegates over ACP it MUST send
`clientCapabilities._meta["com.sprawlcommons/construct"].events = true`.

It MAY send `.turn = true` when it wants turn notifications under the current
method. Deck sends the same `turn` flag for live attach.

### 4.3 The agent chooses notification methods

For an attachment, the agent chooses names from the client's `_meta`, using
this algorithm:

| Client sent | Event channel | Event method | Turn method |
|---|---|---|---|
| new key `.events = true` | lossless | `_com.sprawlcommons/construct/event` | current only if `.turn = true` |
| legacy key `events = true` | lossless | `_construct/event` | legacy (`.turn` has no legacy form) |
| neither | standard `session/update` | — | legacy |

Rules:

- The presence of the new key wins over the legacy key for the event method.
- `.turn` is read only under the new key: `.turn = true` selects
  `_com.sprawlcommons/construct/turn`; anything else selects `_construct/turn`.
- The client MUST accept event notifications under either method when the
  agent advertised `events` under either Construct key, and MUST accept turn
  notifications under either method.
- A client that sent the legacy `events` key gets the legacy method; this is
  how a released Deck keeps its channel.

`conformance/matrix.json` is the normative table for these cases; prose and
matrix must agree. The cases are `current`, `current-events-only`,
`legacy`, `legacy-turn-is-not-a-capability`, `none` and
`both-keys-current-wins`.

### 4.4 Boundary method selection

Deck (the sender) MUST choose:

1. `_com.sprawlcommons/deck/boundary` if the agent advertised
   `_meta["com.sprawlcommons/deck"].boundary = true`;
2. else `_deck/boundary` if it advertised `_meta.deck.boundary = true`;
3. else send nothing.

A Construct agent MUST accept the boundary notification under either method
for the transition release, and MUST apply the same validation and seen-id
deduplication to both.

## 5. Extension methods

All three are JSON-RPC notifications (`method` + `params`, no `id`). Params
MAY carry `_meta`; unknown `_meta` keys MUST be ignored.

### 5.1 Event notification — `_com.sprawlcommons/construct/event`

Sent instead of the standard lossy `session/update` stream when the client
asked for it (4.3). Exactly once per `Event`, in order.

```json
{
  "sessionId": "01J...",
  "event": { "event": "assistant", "message": { "role": "assistant", "content": "hi" } }
}
```

`event` is Construct's journal `Event`, a tagged object whose `event` member is
the kind. Its vocabulary is additive-only; a reader MUST ignore kinds it does
not know. The standard `session/update` mapping remains for clients without
the capability.

### 5.2 Turn state notification — `_com.sprawlcommons/construct/turn`

Sent on every turn-state change and after each successful attachment.

```json
{ "sessionId": "01J...", "turn": 3, "state": "idle", "stopReason": "end_turn" }
```

- `turn` is a per-session unsigned integer, starting at 0 and increasing once
  per prompt that begins.
- `state` is `working`, `waiting` (a permission question is outstanding) or
  `idle`.
- `stopReason` MUST appear only with `idle`, and only when the turn stopped
  with a reason (`end_turn`, `cancelled`, `max_turn_requests`, `error`).

### 5.3 Boundary notification — `_com.sprawlcommons/deck/boundary`

An informational late decision from Deck. It grants nothing; the agent
forwards it to the model and cannot answer it.

```json
{
  "approval_id": "a1f3",
  "destination": "index.crates.io:443",
  "outcome": "allowed",
  "scope": "task",
  "sessionId": "01J..."
}
```

| Field | Required | Meaning |
|---|---|---|
| `approval_id` (alias `id`) | yes | The decision this notes; used for seen-id deduplication |
| `destination` | no | What the blocked request targeted |
| `outcome` (alias `state`) | no | `allowed`, `denied`, …; default `decided` |
| `scope` | no | The reported grant scope; `timed` is defined in §5.4 |
| `expires_at_ms` | required for `scope: "timed"`; otherwise optional | Absolute host grant deadline, Unix milliseconds (§5.4) |
| `sessionId` (alias `session_id`) | no | Target session; absent means every session |

The agent MUST deliver a given `approval_id` at most once, and MUST NOT repeat
one already resolved through a boundary tool.

### 5.4 Timed boundary grants and shared observations (since 1.1.0)

`scope: "timed"` names the host's **Allow for 5 minutes** task grant.
Every timed observation MUST contain `expires_at_ms`: an integer-valued JSON number of
milliseconds since the Unix epoch in the inclusive range 0 through
9007199254740991. It MUST NOT be a string, fractional number, relative duration or null.
As in JSON Schema, `42.0` is integer-valued and normalizes to 42; implementations
MUST accept this representation within the stated range.
Older observations without timed scope remain valid without this field.
Unknown scope strings and additional fields remain permitted for forward
compatibility; a receiver MUST NOT infer authority from them.

Example late decision (same fields under either boundary method):

```json
{
  "approval_id": "a1f3",
  "destination": "index.crates.io:443",
  "outcome": "allowed",
  "scope": "timed",
  "expires_at_ms": 1800000300000,
  "sessionId": "01J..."
}
```

**Host authority and time.** The host computes the deadline once, at the
human decision, as `decision_at_ms + 300000`. It persists that exact deadline
for this task and uses it for every subsequent observation. Traffic, retry,
reconnection, polling and daemon restart MUST NOT move it. A request at
`now_ms >= expires_at_ms` cannot use this grant; the deadline is exclusive.
The host closes active operations relying on that grant at expiry or
revocation, including while its control daemon is unavailable. Other
independently authorized operations are unaffected. Task stop removes the
grant. A later, explicit human decision may create a new grant/deadline; an
agent request cannot do so. Scope matching still preserves task, gateway,
operation, destination and credential name, and all other host policy checks.

This metadata MUST denote the grant deadline, not the pending approval's
expiry or the HTTP long-poll timeout. A sender reports timed scope for an
allowed decision. `once`, `task` and `project` retain their existing meanings;
in particular a once retry-claim window MUST NOT be represented as an active
operation's grant deadline. A task grant MAY report its actual deadline using
the same field; absence of a deadline MUST NOT be described as unlimited
permission. No new grant is implied by an informational record.

**HTTP observations.** The existing read-only boundary endpoint exposes the
same metadata, independently of ACP method spelling:

- `GET /approvals/<id>` and its `?wait=<seconds>` long-poll success response:
  `boundary-status.schema.json`. The existing `state`/`outcome` string aliases
  and nullable/absent scope remain accepted. The path identifies the approval;
  an `approval_id` echo is optional. The wait cap of 300 seconds is a caller
  wait limit, not a grant duration or renewal request.
- `GET /events?after=<seq>`: `boundary-events.schema.json`, either the existing
  array or `{ "events": [...] }` wrapper. Each item is a
  `boundary-event.schema.json` record with `seq`, `approval_id`, and the shared
  state/scope/deadline fields. Sequence handling is unchanged.
- `POST /approvals/<id>/withdraw` remains a withdrawal only. No status,
  event, wait, withdrawal, or ACP notification can approve, extend or recreate
  a grant. No new grant-decision endpoint is introduced here.

When the same decision appears in multiple observations, the host MUST send
the same deadline. These schemas describe successful observations, not HTTP
transport-error bodies or a new tool invocation shape.

**Receiver behavior.** A 1.1 receiver MUST preserve the scope and absolute
deadline in boundary wait/status structured results and model-visible
boundary text (tool-result notes and late decisions). It MUST identify the
timestamp's units, for example `expires_at_ms=1800000300000 (Unix ms)`, or an
unambiguous absolute UTC representation. Existing text for records with no
new metadata SHOULD remain unchanged. It MUST NOT start a new five-minute
window when a record arrives, assume the reported grant is still usable,
automatically replay the blocked command, or generate a permission decision.
The host remains authoritative despite clock skew or delayed delivery.

An already elapsed deadline remains a valid historical observation. The
receiver MUST retain the host's reported outcome and original deadline; it
MAY label the deadline elapsed, but MUST NOT rewrite the host decision or
claim current access. Seen-ID deduplication remains per approval ID across
HTTP tools and both ACP method names: deadline metadata MUST NOT cause a
second delivery or a second authorization. Malformed timed metadata is
rejected before an ID is marked seen, so a corrected record can still arrive.
A malformed HTTP record is an error/ignored invalid event, never an allowed
observation; rejecting it MUST NOT permanently mark the transport unavailable.

**Negotiation and compatibility.** This addition uses the existing `boundary`
capability and §4.4 method selection without another capability or method.
An old reader accepts the scope string and ignores the added timestamp; it
may omit expiry display, but enforcement is always on the host. A new reader
MUST accept old non-timed records and retain the 1.x alias/dual-name rules.
Missing or malformed expiry for the newly defined timed scope is not a
valid 1.1 observation; unknown future fields are not such an error.

## 6. Session setup (Construct parent → Construct child)

`session/new` params may carry the child's setup under
`_meta["com.sprawlcommons/construct"].start`. A reader MUST fall back to
`_meta.construct.start` when the current key is absent. The payload is
Construct's `Start` object: `config` (the child's configuration) and `origin`
(`policy`, `system`, `parent_session`, `parent_call_id`). Both are opaque to
this contract and version with Construct; `cwd` is ACP's own parameter.

Only `construct __child --acp` honours it. A user-mode agent MUST ignore it, so
an ACP client cannot widen the user's configuration.

## 7. Attachment snapshot (Construct agent → client)

The result of `session/load` and the turn state after `session/resume` carry
the current turn under **both** Construct keys:

```json
{
  "_meta": {
    "com.sprawlcommons/construct": { "turn": { "sessionId": "01J...", "turn": 2, "state": "idle" } },
    "construct": { "turn": { "sessionId": "01J...", "turn": 2, "state": "idle" } }
  }
}
```

A client MUST read the current key first, then the legacy key.

## 8. Compatibility

See `compatibility.md`. In short, during contract 1.x:

- a new peer advertises and accepts both names;
- a new sender uses the current name when the peer advertised it, else the
  legacy name;
- a legacy peer keeps working with a new peer in both directions.

A legacy Construct child (pre-1.0) cannot read the current `start` key; parent
and child are the same binary, so this pairing is not a supported upgrade path.

## 9. Removal

The bare names are removed in contract 2.0.0, no earlier than one released
Construct and Deck that both speak contract 1.x. Contract 2.0 also declares
which ACP v2 `_meta` reservation it follows.

## 10. Conformance

Normative artifacts:

- `schema/*.schema.json` — ACP payload and boundary HTTP observation shape.
- `conformance/matrix.json` — names, negotiation cases, accepted names.
- `conformance/payloads.json` — valid and invalid payload examples for every schema.
- `VERSION` — the contract version.

An implementation that vendors a release MUST test the matrix and MUST fail
when `VERSION` and the vendored copy disagree.

Implementations SHOULD validate actual emitted payloads against these schemas,
not only constants or hand-written examples. Unknown fields remain accepted.
Contract 1.0.1 corrects schema omissions without changing the wire: the boundary
ID alias is accepted, load snapshots contain both keys, and a stop reason is
restricted to idle turns, as already specified above.
