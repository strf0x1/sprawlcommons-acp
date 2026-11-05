# SprawlCommons ACP extension contract

Status: normative. Contract version `1.0.1` (see `VERSION`). Applies to ACP
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
| `contract` | `1.0.1` | This document and its schemas |

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
| `scope` | no | The granted scope, if any |
| `sessionId` (alias `session_id`) | no | Target session; absent means every session |

The agent MUST deliver a given `approval_id` at most once, and MUST NOT repeat
one already resolved through a boundary tool.

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

- `schema/*.schema.json` — payload shape.
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
