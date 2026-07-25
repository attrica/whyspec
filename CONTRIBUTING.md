# Contributing

This repository holds the Whyfile specification and its conformance fixtures. It does not
hold the implementation.

## Developer Certificate of Origin

Every commit must be signed off. Add `-s` to your commit command:

```
git commit -s -m "your message"
```

This appends a `Signed-off-by:` line certifying that you wrote the contribution or
otherwise have the right to submit it under the repository's license. The full text is the
[Developer Certificate of Origin 1.1](https://developercertificate.org/). Commits without a
sign-off cannot be merged.

## What a good change looks like

**A change to a normative rule needs a fixture.** Every MUST and MUST NOT in the
specification is required to have at least one valid and one invalid example in `fixtures/`,
and the coverage table has to keep showing no orphan rules and no orphan fixtures. A rule
without a fixture is a rule nobody can check, which in a conformance specification is barely
a rule at all.

**Say what breaks.** A change to the record format or the result envelope affects every
existing record and every implementation that reads one. State plainly which of those a
change breaks — including "none", when that is the answer.

**Additions and meaning-changes are different.** Adding a new optional field is a vocabulary
extension. Changing how an existing field is interpreted is a meaning change, and it needs a
version marker and a migration note. This distinction is normative; it is specified in the
versioning section rather than left to judgement.

## What belongs elsewhere

Bugs in the hosted service or in a client are not specification bugs. If an implementation
disagrees with the specification, that is worth reporting here — say which fixture it fails,
or which rule it appears to contradict, and what it does instead.

## Scope

The specification describes the record format, the result envelope, and the provenance
vocabulary. It deliberately does not describe storage, transport, ranking, or any product
behaviour built on top of these. Proposals to specify those will be declined — not because
they are uninteresting, but because a format specification that also pins an implementation
stops being implementable by anyone else.
