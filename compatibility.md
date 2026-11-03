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
| 2.0.0 | 1, 2 rules declared | TBD | TBD | bare names removed |

Implementations declare the contract version they vendor (Construct:
`CONTRACT.lock`; Deck: its own lock once pinned). A peer that cannot read the
current names is not a supported pairing across major versions; within 1.x it
is.

## Sunset

1. Both halves advertise the current and bare capability keys.
2. Both halves accept the current and bare inbound names.
3. Both halves send the name the peer advertised, else the bare name.
4. One release after both halves ship contract 1.x, contract 2.0.0 removes the
   bare names, `LEGACY_*` constants and dual advertisement.

Removal is a contract major and MUST land as its own coordinated wave.
