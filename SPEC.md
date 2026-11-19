# SprawlCommons ACP extension contract

Status: normative. Contract version `1.6.0` (see `VERSION`). Applies to ACP
protocol version 1, to the HTTP GitHub operation API of §11, and to the HTTP
coordinator task-control API of §13.

The keywords MUST, MUST NOT, SHOULD and MAY are as in RFC 2119.

## 1. Scope

ACP (agentclientprotocol.com) is the wire between Deck and Construct in both
directions:

- Deck is the **client** (it runs a session and sends `session/*` requests).
- Construct is the **agent** for a user session, and the **client** when it
delegates to a child.

ACP only fixes the standard vocabulary. This contract fixes the extensions the
two projects share, and the compatibility window while released peers still
speak the old names. Since 1.2.0 it also fixes the GitHub operation API (§11):
an HTTP wire between an agent in a Deck sandbox and Deck's host gateway,
which both projects implement and which therefore versions here. Since
1.4.0 it also fixes the coordinator task-control API (§13), the same kind of
HTTP wire between a coordinator task and Deck's host gateway.

ACP reserves `_`-prefixed methods for extensions and, in v2, reserves
unprefixed `_meta` keys. Extension `_meta` keys therefore use a reverse-DNS
namespace: `com.sprawlcommons/<product>`, and extension methods are
`_com.sprawlcommons/<product>/<name>`.

## 2. Versioning

Two axes are independent and MUST both be declared by an implementation:

| Axis | This release | Meaning |
|---|---|---|
| `acp` | `1` | The ACP protocol version the peer speaks |
| `contract` | `1.6.0` | This document and its schemas |

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
- `github_operations` (since 1.2.0) is an integer under the current Deck key
  only; see §11.1.
- `idempotentPrompts` (since 1.3.0) is a boolean under the current Construct
  key only; see §12.1.

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

- `schema/*.schema.json` — ACP payload, boundary HTTP observation, GitHub
  operation (`github-*`) and coordinator control (`control-*`) shape.
- `conformance/matrix.json` — names, negotiation cases, accepted names, and
  under `github` the operation table, limits, refusal table and publish
  framing cases, and under `control` the coordinator operation table,
  limits, refusal table and request exchanges (§13).
- `conformance/payloads.json` — valid and invalid payload examples for every schema.
- `VERSION` — the contract version.

An implementation that vendors a release MUST test the matrix and MUST fail
when `VERSION` and the vendored copy disagree.

Implementations SHOULD validate actual emitted payloads against these schemas,
not only constants or hand-written examples. Unknown fields remain accepted.
Contract 1.0.1 corrects schema omissions without changing the wire: the boundary
ID alias is accepted, load snapshots contain both keys, and a stop reason is
restricted to idle turns, as already specified above.

## 11. GitHub operation API (since 1.2.0)

A Deck VM task has no IP route and no GitHub credential. It publishes through
a closed set of operations that Deck's host gateway performs with a host-held
token (Deck ADR 0007, ADR 0008). This section is the wire between the
gateway (the **server**, implemented by Deck) and the agent's tool that calls
it (the **client**, implemented by Construct's `developer` tool and by
`deck-fake-agent`). It is not an ACP method; it is versioned here because two
implementations depend on it. Host policy (which repository, which branches,
whether a write asks the user) is the server's and is not specified here
beyond what the client observes.

### 11.1 Discovery and capability

- The server is reachable at the URL in the guest environment variable
  `DECK_GITHUB_URL` (HTTP/1.1, plain, one request per connection). It is set
  only when the task has a repository; a client MUST treat its absence as "no
  GitHub publication from this sandbox" and MUST NOT fall back to `git push`,
  `gh`, or any other route.
- An agent whose client speaks this API advertises
  `agentCapabilities._meta["com.sprawlcommons/deck"].github_operations` in its
  `initialize` response: the highest API version it speaks. This contract
  defines version `1`. The capability exists only under the current key; it
  has no legacy (`deck`) form, and a reader MUST NOT look for one. A reader
  treats an absent, non-integer or `0` value as "does not speak it". Deck
  uses it only to tell the user that an agent cannot publish from a sandbox;
  it grants nothing.
- The client learns its destination from `refs` (§11.4), never from the
  environment. No repository, base, task id or branch is in the guest
  environment for this purpose.

### 11.2 Requests

Every operation is `POST` to its own path with a JSON object body. The body's
`operation` field MUST equal the operation the path serves.

| Operation | Path | Writes | Request schema | Success schema |
|---|---|---|---|---|
| `publish` | `/operations/publish` | yes | `github-publish-request` (+ bundle, §11.3) | `github-publish-response` |
| `refs` | `/operations/refs` | no | `github-refs-request` | `github-refs-response` |
| `create_pr` | `/operations/pull_request` | yes | `github-create-pr-request` | `github-pull-request` |
| `update_pr` | `/operations/pull_request/update` | yes | `github-update-pr-request` | `github-pull-request` |
| `review` | `/operations/pull_request/review` | no | `github-review-request` | `github-review-response` |

Rules:

- The JSON object is at most 65536 bytes. Requests are closed:
  `additionalProperties` is false, and the server MUST refuse an unknown field
  with `deck_bad_request` rather than ignore it, so a client never believes it
  got a capability it did not.
- A branch is a name without `refs/heads/`, at most 200 bytes, of ASCII
  letters, digits and `._-/`, with no empty, `.`-leading, `.`-trailing or
  `.lock`-suffixed component, no `..`, not `HEAD` and not starting with `-`.
  The schemas check the alphabet and length; the server checks the rest.
- `create_pr` requires `head`, `base` and a non-blank `title`; `body` defaults
  to empty and `draft` to `true`. `update_pr` requires `number` and at least one
  of `title`, `body`, `base`, `draft`; a present `body`, including `""`, sets
  the body. The title and body together are at most 65536 bytes.
- A request whose operation is not in the set is refused, never forwarded.
  The names `merge`, `close`, `delete`, `tag`, `release`, `force_push`,
  `workflow`, `dispatch` and `settings` are refused by name with
  `deck_not_permitted` (403) and a message that lists what a task may do; any
  other unknown path is `deck_not_permitted` (404). A method other than `POST`
  is `deck_bad_request` (405).
- `publish` MAY carry `summary: { subject, count }`: the subject of the commit
  being published (at most 256 characters) and how many commits are new. It is
  guest-supplied description that the server MAY show on an approval card,
  labelled as such. It decides nothing: the commit that lands is the one in
  the bundle, which the server reads itself. A `create_pr`/`update_pr` card
  is described from the request's own `title` and `draft`, so those
  operations have no `summary` field.

### 11.3 Publish framing

A `publish` body is the JSON object, immediately followed by a 4-byte
big-endian unsigned length `n`, then exactly `n` bytes of a git bundle. One
`content-length` covers all three; chunked bodies are refused. The JSON
object ends where its top-level value ends; there is no separator.

- `n` is at most 16777216; a larger declared length is refused (413) before
  anything is read or allocated. A body with no length prefix is 411; one that
  ends inside the bundle is 400.
- The bundle is `# v2 git bundle` with exactly one ref line naming
  `refs/heads/<branch>` for the request's `branch`, optionally preceded by
  prerequisite lines (`-<sha> [subject]`), then a blank line, then the pack.
  Any other header line, a second ref, another ref name or another version is
  refused (400) before `git` runs.
- An incremental bundle names the branch's published tip as its prerequisite.
  The server fetches the remote tip first, so a prerequisite resolves however
  the branch was last pushed; one that is not on the branch is
  `deck_bad_request`.
- The publish is fast-forward only. If the branch has a commit that is not an
  ancestor of the bundle's, the reply is `deck_github_refused` (403) with
  `current`: the client rebases onto it and publishes again; it MUST NOT
  retry the same bundle. If the branch moved during the publish, the reply is
  `deck_github_conflict` (409, retryable) with `current`.

`matrix.json` `github.framing_cases` carries whole bodies (base64) and what a
server must conclude from each; both implementations SHOULD test their
encoder or parser against them.

### 11.4 Responses

A success is `200` with the operation's success schema. Every success has a
`domain` string, the destination the server recorded (`owner/name#branch`,
`owner/name#pr7`, or `owner/name`). Responses are open: a client MUST ignore
fields it does not know.

- `publish`: `repository`, `branch`, `commit` (40 hex), `previous` (the prior
  tip, `null` when the branch was created) and `created`.
- `refs`: `repository` (`owner/name`, lowercased), `base` (the only base a
  pull request may target), `task_branch` (this task's own branch, present
  before it exists on GitHub), `writable` (every branch this task may write;
  it always contains `task_branch`) and `branches` (`branch`, `commit`,
  `task_branch`). The server is the authority; a client builds its bundle for
  a branch in `writable` and opens pull requests against `base`.
- `create_pr`/`update_pr`: the pull request summary: `number`, `title`,
  `state` (`open`/`closed`), `draft`, `head`, `head_commit`, `base`,
  `mergeable` (`null` while GitHub computes it), `html_url`, and optionally
  `merged`.
- `review`: the summary plus `merged` (required) and `checks`: `null` when the
  head commit is unknown, else `{ total, runs: [{ name, status, conclusion }] }`
  with at most 100 runs. `status` and `conclusion` are GitHub's strings, passed
  through; a client MUST NOT reject one it does not know.

### 11.5 Refusals

Every non-2xx body, including transport refusals before an operation is
parsed, is `github-error`: `error.{message, type, code}` with `type` equal to
`code`, and `retryable`. `current` (40 hex) appears only with
`deck_github_refused` (a rewrite) or `deck_github_conflict` (required).
`approval_id` appears only with `deck_boundary_denied`, and the same id is in
an `x-deck-approval` response header. Messages are bounded and never contain
a credential.

| Code | Status | Retryable | The client should |
|---|---|---|---|
| `deck_github_refused` | 403 | no | Do something else: a branch, base or pull request this task may not touch, or a rewrite (`current` names the commit to rebase onto). |
| `deck_github_conflict` | 409 | yes | Rebuild on `current`, then publish again. |
| `deck_bad_request` | 400, 405, 408, 411, 413, 431 | no | Fix the request or bundle. |
| `deck_github_not_found` | 404 | no | GitHub has no such pull request. |
| `deck_github_rejected` | 409, 422 | no | GitHub refused it (e.g. a pull request already exists, a protected-branch hook); its reason is the message. |
| `deck_github_credential` | 502 | no | Report it; the host's token is the user's to fix. |
| `deck_github_failed` | 502 | yes | Retry later: GitHub or git was unreachable or rate limited. |
| `deck_not_permitted` | 403, 404 | no | Stop: the operation is not in the set. |
| `deck_boundary_denied` | 403 | per body | `retryable: true` with `approval_id`: the user has not decided; retry after they do. `false`: denied by policy. |
| `deck_boundary_unavailable` | 502 | yes | Retry later: the approval queue could not be reached. |
| `deck_credential_missing` | 503 | no | Report it: no credential is configured. |
| `deck_credential_unavailable` | 503 | yes | Retry later: the store could not be read now. |
| `deck_credential_refused` | 403 | no | Report it: the user refused the credential read. |
| `deck_credential_revoked` | 403 | no | Stop: the credential was revoked during the operation; a ref already pushed stays pushed. |

A client MUST surface the message to the model and MUST NOT turn any refusal
into an attempt on another route. A `retryable: false` refusal MUST NOT be
retried unchanged.

### 11.6 Compatibility

This API is new in 1.2.0 and additive: no ACP name, capability or payload
defined earlier changes, and a peer that ignores it is unaffected. A 1.1
Deck never sets `DECK_GITHUB_URL` for a client to find; a 1.1 Construct does
not advertise `github_operations`, so a 1.2 Deck reports that it cannot
publish from a sandbox instead of letting a push fail. Within 1.x, fields are
only added to responses, and an added request field is optional and refused
by a server that does not know it, so an older server fails a newer client
loudly. A new operation is a new path and a new API version.

## 12. Idempotent prompts (since 1.3.0)

A client that never receives the response to `session/prompt` cannot tell
whether the agent took the prompt. This happens when the agent's process, its
VM or the connection dies. Without a key, sending the prompt again can run it
twice. This section gives ACP v1 the prompt key that ACP v2 defines as
`PromptRequest.idempotencyKey`, with the same name and rules, adapted to v1's
response (the stop reason, sent when the turn ends). Contract 2.0 moves the
field to v2's top-level parameter. Its meaning does not change.

### 12.1 Capability

An agent that implements this section advertises
`agentCapabilities._meta["com.sprawlcommons/construct"].idempotentPrompts = true`,
under the current key only. A client MUST NOT send a key to an agent that did
not advertise it. An agent that does not know the field ignores it, like any
unknown `_meta` member, and would run a resent prompt again.

### 12.2 The key

`session/prompt` params carry it under the current Construct key:

```json
{
  "sessionId": "01J...",
  "prompt": [{ "type": "text", "text": "Run the database migration" }],
  "_meta": {
    "com.sprawlcommons/construct": { "idempotencyKey": "0b6f3c1e-8d2a-4c57-9a41-5e2f7d90c3ab" }
  }
}
```

- The field is optional. Omitted and `null` are equivalent and mean no key; the
  agent then handles the prompt without duplicate detection.
- When present, the key is an opaque, case-sensitive string of 1 to 255
  characters. The agent MUST reject any other value with `-32602` (Invalid
  params) and MUST NOT treat it as omitted.
- A key is scoped to the session named by `sessionId`. The same string in
  another session names an unrelated prompt.
- There is no legacy form. The legacy `construct` key does not carry it.

### 12.3 The client

- The client generates the key when the user submits the input, and stores it
  with the pending input. It SHOULD use a UUID (RFC 9562) or another random
  value with at least as much entropy, and SHOULD NOT derive it from user
  content or put sensitive data in it.
- One key identifies one prompt. The client sends the same key on every
  attempt, including after it reconnects, reattaches (`session/load`) or
  restarts. It uses a new key for a new prompt, including when the user sends
  the same text again on purpose.
- A client MUST NOT send the same key with a different prompt.
- Each attempt is its own JSON-RPC request with its own `id`.

### 12.4 The agent

The agent records the key with the prompt at the point where the prompt
becomes part of the session: in Construct, on the journaled record of the
submitted prompt, written before the turn starts. The key MUST be at least as
durable as the prompt, and it is retained for as long as the session can be
loaded. Recording it later would reopen the window this section closes.

On a request with a key, the agent looks the key up in the session:

| What the agent has recorded for the key | What the agent does |
|---|---|
| Nothing | Handles the prompt as usual, and records the key with it. |
| A prompt still waiting to start (queued behind a running turn) | Does not queue a second prompt. Answers this request when it answers the first one, with the same outcome. |
| A prompt whose turn is running | Does not start a turn. Answers this request when that turn ends, with its stop reason. |
| A prompt whose turn ended with a stop reason | Does not start a turn. Answers at once with that stop reason. |
| A prompt whose turn never recorded a stop reason (the agent restarted mid-turn) | Does not start a turn. Answers at once with `cancelled`. Recovery may leave the session idle, and the client decides whether to send a new prompt. |

These cases are `idempotent_prompts.cases` in `conformance/matrix.json`.

- **No second turn.** A request answered from a recorded key starts no turn,
  inserts no user message, does not increase the turn number of §5.2 and adds
  nothing to the session's history.
- **A reused key.** The agent MUST NOT run a second prompt for a recorded key.
  If a request carries a recorded key with a different prompt, the agent
  either answers as for a retry or, when it notices the difference, rejects the
  request with `-32602` (Invalid params). When it rejects, the error's `data`
  MUST be `{ "reason": "idempotency_key_conflict" }`. Agents are not required to
  compare prompts; Construct compares them and rejects. After a rejection, the
  key stays recorded for the first prompt.
- **Errors leave the key unused.** A prompt the agent refused before recording
  it (for example an unknown session) records nothing, and the client can send
  the same prompt with the same key again.
- **Cancelling.** `session/cancel` ends the running turn as usual. Every
  request waiting on that turn's key gets the turn's `cancelled` stop reason.
- **Keys stay private.** The agent MUST NOT echo a key in event notifications
  (§5.1), turn notifications (§5.2), attachment snapshots (§7), replayed
  history or the standard `session/update` stream. A key is not a credential.
  It only has meaning in a session the caller can already prompt.

### 12.5 Compatibility

Additive. A 1.2 client never sends a key, and a 1.3 agent behaves as before.
A 1.3 client talking to a 1.2 agent sees no `idempotentPrompts` and sends no
key. Like any 1.2 client, it cannot tell whether a prompt whose response was
lost ran, so it SHOULD ask the user rather than resend on its own. A 1.3 agent
that advertises the capability and gets a malformed key rejects it. It never
runs the prompt without the key, so a client bug fails loudly.

## 13. Coordinator task control (since 1.4.0)

A project coordinator is a task whose agent directs other tasks: it creates
workers, prompts them, waits for their turns and stops them (Deck ADR 0011
§4). It does so through one closed HTTP operation endpoint on Deck's host
gateway. This section is the wire between that gateway (the **server**,
implemented by Deck's `deckd`) and the agent's tool that calls it (the
**client**, implemented by Construct's `deck` tool). Like §11 it is not an
ACP method; it versions here because both implementations depend on it.
What a coordinator may do (its project set, caps and budgets) is the user's
policy, held by the host and never editable by the guest; this section fixes
only what the client observes of it.

The gateway carries and the host decides. No operation here asks the user:
an operation outside policy is refused with a code, the coordinator reports
it, and the user changes the policy in Deck. There is no approval,
credential, grant, destroy, resume, start, budget-change or publication
operation, and no full-transcript read.

### 13.1 Discovery

- The server is reachable at the URL in the agent's environment variable
  `DECK_CONTROL_URL`. The host sets it only for a coordinator task, and only
  when it serves this surface. A client exposes its control tool only when
  the variable is set; an absent variable means "this task controls no other
  task". No `initialize` capability is defined or needed.
- The value is exactly `http://<host>:<port>` with `<host>` a loopback
  literal, `127.0.0.1` or `[::1]`, and no userinfo, path, query, fragment or
  trailing slash. The client sends to `<DECK_CONTROL_URL>/control`. A client
  MUST treat any other value as absent and MUST NOT send to it.
- In a VM task the address is the guest's loopback, mapped by `deck-egress`
  to the host (Deck ADR 0004 §1); only the guest can reach it. A coordinator
  on Deck's local backend gets a host loopback address, which other host
  processes can also reach; the host then also sets `DECK_CONTROL_TOKEN`
  (§13.2).
- Worker tasks never get either variable.

### 13.2 Authorization

`DECK_CONTROL_TOKEN` is a per-task bearer token: 32 to 256 characters of
the RFC 6750 `b64token` alphabet (`A-Z a-z 0-9 - . _ ~ + /`, then optional
`=`). The host generates it from a cryptographically secure source with at
least 128 bits of entropy, gives each coordinator task its own, and MUST set
it whenever `DECK_CONTROL_URL` names a host address. It MAY leave it unset
when the address is a VM guest's loopback.

- **Token set.** The client sends `Authorization: Bearer <token>` on every
  request, reading the variable when it sends. The server checks the header
  before it reads the body, the path or the method: a missing header, more
  than one, another scheme, or a token that differs (compared in constant
  time; the scheme name is case-insensitive) is refused with 401,
  `deck_control_unauthorized` (`retryable: false`) and
  `WWW-Authenticate: Bearer realm="deck-control"`. An unauthenticated caller
  learns nothing else, not even whether its body was well formed.
- **Token unset.** The client sends no `Authorization` header. The server
  neither requires nor checks one, and ignores one that arrives.
- The token appears in no reply, no task summary, no event, no log and never
  in `DECK_CONTROL_URL`. The server MUST NOT send CORS
  (`Access-Control-Allow-*`) headers, so a web page cannot attach the header
  from a browser.

The token keeps other host processes (other users' processes, other tasks'
agents, a local web page) off the surface. It does not confine the agent
itself: every process the coordinator's agent runs inherits its environment
and can use the token. What the coordinator may do is bounded by its policy,
which the host enforces on every operation, with or without a token.

### 13.3 Requests

Every request is `POST /control` over HTTP/1.1, one request per connection,
with a `content-length` and a body of one JSON object of at most 32768
bytes. Chunked bodies are refused. The object's `operation` field names one
operation of a closed set:

| Operation | Input | Success reply | Request schema | Success schema |
|---|---|---|---|---|
| `tasks` | `project?` | `{ tasks, truncated, projects }`: at most 200 summaries and the project set | `control-tasks-request` | `control-tasks-response` |
| `task` | `id` | `{ task }`: one summary | `control-task-request` | `control-task-response` |
| `create` | `project?`, `brief`, `title?`, `budget?` | `{ id }` | `control-create-request` | `control-create-response` |
| `integrate` (since 1.6.0) | `project?`, `destination`, `contributors`, `brief`, `title?`, `budget?` | `{ id }` | `control-integrate-request` | `control-integrate-response` |
| `prompt` | `id`, `text` | `{ turn }` | `control-prompt-request` | `control-prompt-response` |
| `wait` | `id`, `after_turn?`, `wait_ms` | `{ timed_out, task }` | `control-wait-request` | `control-wait-response` |
| `stop` | `id` | `{ id, state }` | `control-stop-request` | `control-stop-response` |

Requests are closed: `additionalProperties` is false, and the server refuses
an unknown field with `deck_control_bad_request` rather than ignore it. A
missing or non-string `operation` is `deck_control_bad_request` (400); a
string that is not in the set is `deck_control_refused` (403), and the
message lists the set. Another path is `deck_control_bad_request` (404),
another method 405, no `content-length` 411, and a larger body 413, refused
before it is read.

**Scope.** A coordinator's scope is the project set in its policy. A task is
in scope when its project is. A project outside the set is
`deck_control_scope`. A task outside the set is `deck_control_unknown`,
exactly as a task that does not exist, so the surface never discloses tasks
the coordinator may not see. The coordinator itself is never in `tasks`.
`prompt` or `stop` naming any coordinator, and `wait` naming the caller
itself, are `deck_control_refused`. Since 1.5.0 a `deck_control_scope`
message names the project ids in the set, so the model can correct the
request without asking the user.

- **`tasks`** lists the summaries (§13.4) of tasks in scope, limited to
  `project` when it is given, most recently created first. At most 200 are
  returned. The server may return fewer to fit the reply size limit.
  `truncated` is true when more summaries are available. Since 1.5.0 the
  reply also carries the coordinator's whole project set in `projects` as
  `{ id, name }` entries. The `id` is the project key that `create` and
  `tasks` take. The `name` is the name the user sees in Deck. The reply
  includes the project set even if no task exists yet. A client
  reading a 1.4 server finds no `projects` and MUST NOT fail on that.
- **`task`** returns one summary.
- **`create`** records a worker in `project`, starts it, and delivers `brief`
  as its first prompt once its session is up. It returns the new id as soon
  as the task is recorded, before the agent has started. The worker's
  `created_by` is the coordinator's id. The worker runs the project's recorded
  agent command under the project's GitHub policy: the coordinator cannot
  choose a command, a repository or a base. `title` (1 to 80 characters)
  replaces the default title. `budget` (`requests` and/or `tokens`, positive
  integers) may lower the policy's per-worker budget, never raise it: a value
  above it is `deck_control_refused`, as is a project with no recorded agent
  command. Reaching the policy's concurrency cap (live workers this
  coordinator created) or creation rate (per rolling hour) is
  `deck_control_cap`. Since 1.5.0 `project` may be omitted: when the
  coordinator's project set has exactly one project, the server uses it;
  otherwise it refuses with `deck_control_bad_request` (400) and the message
  names the set's ids. A client SHOULD omit it unless the set has more than
  one project.
- **`integrate`** reserves and prepares a worker to combine contributor
  commits in order. It uses the project resolution, command, provenance,
  title, budget and caps of `create`. See §13.7.
- **`prompt`** sends `text` to an idle task and returns the number of the
  turn it began (§5.2: turns count from 0 and the first prompt begins turn 1).
  A task whose turn is `working` or `waiting` is `deck_control_busy`. A task
  that was just created and has no session yet is waited for, at most 60
  seconds, and is then `deck_control_busy`. An integration waiting for
  inputs returns `deck_control_busy` immediately with the waiting reason.
  This surface returns `deck_control_refused` for a `stopped`, `failed` or
  `destroyed` task.
- **`wait`** is a long poll. `wait_ms` is required, an integer from 0 to
  300000 (300 s); a larger value is `deck_control_bad_request`, never
  silently shortened. `after_turn` defaults to 0. The server replies
  `timed_out: false` as soon as one of these holds, checking first when the
  request arrives:
  1. the task's lifecycle state is `stopped`, `failed` or `destroyed`;
  2. its turn is `idle` and its number is greater than `after_turn`;
  3. a pending approval or a `waiting` permission question appeared after
     the request arrived;
  4. since 1.6.0, the integration's preparation is waiting for input.

  Otherwise, after `wait_ms`, it replies `timed_out: true`. Either way the
  reply carries the task's current summary, and its status is 200: the time
  running out is the expected end of a long poll, not a failure, and the
  reply answers the same question a `task` would. After `create`,
  `wait { id, wait_ms }` returns when the brief's turn ends; after `prompt`
  returned `{ turn: n }`, `wait { id, after_turn: n - 1, wait_ms }` returns
  when that turn ends. A client's HTTP timeout MUST exceed `wait_ms`.
- **`stop`** stops the task's agent and returns its lifecycle state once the
  stop is confirmed or has failed. Stopping a task that is not running
  returns its state unchanged. The task's record stays; nothing is destroyed.

### 13.4 Task summary and replies

A success is `200` with the operation's success schema. Replies are open: a
client MUST ignore fields it does not know. A reply body is at most 1 MiB.

A task summary (`control-task-summary`) has:

| Field | Meaning |
|---|---|
| `id` | The task's id. |
| `project` | Its project key (Deck ADR 0010). |
| `title` | The first line of its first prompt, or `create`'s `title`; at most 80 characters; `null` before either exists. |
| `state` | Lifecycle: `created`, `running`, `stopped`, `failed` or `destroyed`. |
| `turn` | `{ number, state, stopReason? }` with §5.2's meaning and vocabulary; `null` before the host has seen a turn. |
| `attention` | Why it needs a person now, or `null`: `approval`, `question`, `finished` or `failed` (Deck ADR 0010 §6). Since 1.6.0, `integration_input` means integration preparation is waiting. A reader treats an unknown value as "needs a person". |
| `pending_approvals` | How many boundary approvals for it are pending in the host's queue. |
| `publication` | Its latest publication (Deck ADR 0008 §8), or `null`: `{ kind: "branch", branch, commit }` or `{ kind: "pull_request", number, url, title, draft }`. |
| `pull_request` | The last read live state of its pull request, or `null`: `{ number, state, draft, merged, html_url }`. |
| `created_by` | The coordinator that created it, or `null` for a task the user created. |
| `last_message` | The text of its last assistant message, at most 2048 bytes of UTF-8 cut at a character boundary, or `null`. `last_message_truncated` is true when it was cut. |
| `integration` | Preparation and pinned inputs for an integration worker since 1.6.0, as `control-integration` (see §13.7). Absent for other workers. |
| `worktree` | A local worker's managed Git worktree since 1.7.0. It carries `branch`, the task branch without `refs/heads/`, and `base_commit`, its full starting commit ID. `target_ref` is the full local branch ref when known. |

In `task` and `wait`, `worktree.review_commit` may name the full commit ID
at the task branch tip. It is present only when the branch has advanced from
its recorded start and contains the start in its ancestry. For an integration
worker it also contains each pinned contributor commit. It describes the
committed branch and does not account for uncommitted files. A `tasks`
listing may omit the review commit.

A summary never carries a transcript, a prompt other than its title, a
credential, a token or a local worktree path.

### 13.5 Refusals

Every non-2xx body, including transport refusals, is `control-error`:
`error.{message, type, code}` with `type` equal to `code`, and `retryable`.
Messages are at most 4096 characters and never contain a credential or the
token.

| Code | Status | Retryable | The client should |
|---|---|---|---|
| `deck_control_bad_request` | 400, 404, 405, 411, 413 | no | Fix the request. |
| `deck_control_unauthorized` | 401 | no | Stop: `DECK_CONTROL_TOKEN` is missing, stale or not sent. |
| `deck_control_scope` | 403 | no | Report it: the project is outside this coordinator's project set. |
| `deck_control_cap` | 403 | yes | Report it, then retry after a worker ends or the hour rolls; the user may raise the cap. |
| `deck_control_refused` | 403 | no | Do something else: the host will not do this as asked (an operation outside the set, a budget above the ceiling, a project with no agent command, a stopped task, the coordinator itself). |
| `deck_control_unknown` | 404 | no | The task does not exist or is outside scope. |
| `deck_control_busy` | 409 | yes | Wait for the task or destination identified by the message to become available. |
| `deck_control_unavailable` | 503 | yes | Retry later: the gateway could not reach `deckd`. |

A client MUST surface the message to the model. A `retryable: false`
refusal MUST NOT be retried unchanged, and no refusal is a reason to reach
the host by another route.

`matrix.json` `control.exchanges` carries whole requests (token, headers,
body) and the status, code or reply a server must produce for each, with and
without the bearer header; both implementations SHOULD test against them.

### 13.6 Compatibility

New in 1.4.0 and additive: no ACP name, capability or payload defined
earlier changes, and no `initialize` field is added. A 1.3 Deck never sets
`DECK_CONTROL_URL`, so a 1.4 Construct offers no control tool; a 1.3
Construct ignores the variables, so its coordinator simply cannot control
tasks. Within 1.x, fields are only added to replies, a new request field is
optional and refused by a server that does not know it, a new refusal code is
a minor release, and a new operation is a minor release that an older server
refuses with `deck_control_refused`.

1.5.0 is additive in that sense. `create`'s `project` becomes optional, so a
1.4 server refuses a `create` without it as `deck_control_bad_request`; a
1.5 client that may meet a 1.4 server sends `project` (it is in every
`tasks` summary, and in a 1.5 `tasks` reply's `projects`). `tasks` gains the
reply field `projects`, which a 1.4 client ignores.

1.6.0 adds `integrate` and the optional summary field `integration`. A
1.5 server refuses `integrate` with `deck_control_refused`. The client MUST
surface the refusal and MUST NOT substitute an ordinary `create` for it.
A 1.5 client can use the other operations and ignores the new reply field.

### 13.7 Integration workers (since 1.6.0)

The coordinator supplies an ordered list of 1 to 16 distinct contributor
task IDs from the chosen project. The server resolves them from its own
records. A missing or out-of-scope task returns `deck_control_unknown`.
The server refuses a coordinator as a contributor and refuses inputs from
an incompatible repository. The request carries no paths, repository
URLs, commit IDs, agent commands or publication grants.

| `destination.kind` | Selector | Starting commit | Review result |
|---|---|---|---|
| `local_branch` | `branch`, a branch name without `refs/heads/`, per §11.2 | The branch tip in the exact local source repository | The integration worker's own local branch |
| `new_pull_request` | The project's configured GitHub repository and base | The current tip of that base on GitHub | A draft PR from the integration worker's own branch, under the existing publication approval policy |
| `existing_pull_request` | `number`, an open PR in the project's configured GitHub repository | The current PR head | The integration worker's own published branch, for the user to apply |

The destination selects the required backend. A server that cannot run
that backend refuses the request. It reserves one active integration per
destination before starting preparation. The destination key uses the
exact source repository and branch for a local target, or the normalized
GitHub repository with the configured base or PR number for a remote
target. The server records the key with the task and uses it for the
lifetime of the reservation. The reservation covers preparation, a live
worker and unconfirmed shutdown. The server also checks the reservation
whenever it starts or resumes an integration worker.

A repeat by the same coordinator for the same project, destination and
ordered contributors returns the active worker's ID without consuming a
second slot or replacing its brief or pins. If no preparation is in flight,
the repeat retries waiting or interrupted preparation on the same worker.
A different request for the reserved destination returns
`deck_control_busy`. The message MAY name the active task only if the caller
can see it under §13.3. The user can release a reservation before launch by
destroying the task in Deck.

The server records the destination's starting commit and each contributor
commit as full object IDs. A local input comes from the contributor's
recorded task branch in the source repository. A VM input comes from the
contributor's published task branch in the authorized repository. A
later ref movement MUST NOT substitute a different commit for a recorded
pin. When a required commit cannot be obtained, the task's
`integration.phase` is `waiting` with a `reason` of at most 512
characters, and its resolved pins remain visible. This wait precedes the
agent turn and does not change the meaning of `turn.state`.

When the checkout is ready, the server starts the worker in its own
checkout at the recorded starting commit. The first prompt includes the
ordered exact commits, the contributor briefs and the integration brief.
It asks the worker to combine those commits, resolve conflicts, run the
combined tests, and report its resolutions and test results in its normal
conversation. Deck's existing task conversation can also surface a
decision the worker needs. The worker's result uses its own branch and
leaves the destination and contributor refs untouched. The result must
contain the starting commit and all pinned contributor commits in its
ancestry. GitHub publication uses the project's approval mode and
restricts writes to the integration worker's own branch. The existing
PR and its head branch are read-only for the integration worker.

The summary carries the destination selector, the worker's review branch,
the phase (`preparing`, `waiting` or `ready`), and the ordered
contributors as `{ id, commit? }`. `base_commit` and each `commit`
appear when pinned and are required by `ready`. `ready` means the input
checkout has been prepared. The worker's normal turn and publication
fields report its progress after that. For remote destinations, the summary
also carries the recorded `repository`. For a new PR, it also carries the
recorded `base_branch`.
