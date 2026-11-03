# Working on the contract

This repository is the single source of truth for the ACP extension wire
between Deck and Construct. Read `SPEC.md` and `conformance/matrix.json`
before touching a name, a capability or a payload.

## The rule

**No implementation-only wire change.** A change to a method name, `_meta`
key, capability flag or payload shape starts here, then lands in both
implementations pinned to a release. A PR that changes the wire in Construct
or Deck without a contract version is rejected.

## A change, in order

1. Open an issue with the compatibility impact: which peers break, and whether
   the change can be additive.
2. Open a PR here. In the same PR:
   - `SPEC.md` (normative prose),
   - `schema/` if a payload changed,
   - `conformance/matrix.json` if negotiation changed,
   - `compatibility.md` and the support table,
   - `CHANGELOG.md` and `VERSION`.
3. Bump `VERSION` by semver: patch (prose/fixture), minor (additive), major
   (rename/removal or changed meaning). A rename is always major.
4. Merge, tag `v<VERSION>`, publish the release.
5. In Construct and Deck, bump the vendored pin and `CONTRACT.lock` in the
   same wave. Each implementation PR cites `contract@<VERSION> §…` and adds
   the failing-before test for its side.

## Compatibility rules for authors

- A current sender uses the current name only when the peer advertised it;
  otherwise it falls back to the bare name.
- A current receiver accepts both forms for the whole 1.x line.
- Do not remove a bare name in a minor. Removal is a contract major, after one
  released pair that speaks 1.x.
- Never make a payload change that an old reader would misread as a different
  meaning. Add fields; do not repurpose them.

## Machine artifacts

`conformance/matrix.json` is the negotiation table; both repositories iterate
it in tests. `schema/*.schema.json` is normative for shape. Prose that
disagrees with them is a bug in the prose.
