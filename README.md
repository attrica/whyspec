# The Whyspec specification

[![Spec conformance](https://github.com/attrica/whyspec/actions/workflows/conformance.yml/badge.svg)](https://github.com/attrica/whyspec/actions/workflows/conformance.yml)
[![License](https://img.shields.io/github/license/attrica/whyspec)](LICENSE)

The open specification behind **Attrica** — *Why this, not that.*

A **why record** is a decision record: a markdown file, in your own repository, that says what
was decided, what the alternatives were, and why one was chosen. It exists because the reasoning
behind a change is the part that doesn't survive — diffs survive, tests survive, the argument
that produced them does not. A why record makes that argument a file: greppable, reviewable,
diffable, and readable by a tool nobody has written yet. It's a generic noun, not a proper noun —
like "an OpenAPI document" — conventionally kept under `docs/decisions/`.

The `why` tool — always lowercase, always monospace — is the vendor-neutral name for anything
that reads or writes them: a CLI, a library, an editor plugin, a CI check.

A complete, conforming why record:

```markdown
# Decision: Store session state in the primary database

**Status:** Accepted
**Date:** 2026-08-18

## Context

Where should session state live? The shared cache is already deployed and
the primary database is not sized for per-request reads.

## Decision

Sessions live in the primary database. A cache eviction would log every
user out, and the reconnect storm costs more than the reads it saves.

## Alternatives considered

1. Shared cache keyed by session id — rejected: eviction logs everyone out.
2. Signed client-side cookie — deferred: revisit once payload size settles.
```

This repository specifies three things, and nothing else:

- **the record format** — how a why record is written and parsed
- **the result envelope** — the shape of an answer to a query
- **the provenance vocabulary** — the tiers a claim can come from, and what each is worth

## Whyspec and MADR

Whyspec is a superset of [MADR](https://adr.github.io/madr/), not a rival to it: a record
written to the MADR template is already a valid why record. [REC-145](spec/whyspec-draft.md)
requires a conforming parser to accept MADR's section spellings — `Context and Problem
Statement`, `Decision Outcome`, `Considered Options` — as aliases for its own, alongside MADR's
own heading and status conventions. What Whyspec adds on top is a provenance tier: not just that
a decision was recorded, but how it came to be known — `authored` by a person, `captured` from a
conversation, `attested` by review, or `reconstructed` after the fact.

It also carries the **capture-decision skill**
([`skills/capture-decision/SKILL.md`](skills/capture-decision/SKILL.md)): the teachable form of
the convention — where a record goes, the shape it takes, and the traps that silently un-record
it. Every parser-behaviour claim in it is validated against the reference implementation.

## Implementing this specification

Read [`spec/whyspec-draft.md`](spec/whyspec-draft.md), then build against
[`fixtures/`](fixtures/README.md): a machine-checkable corpus of valid and invalid examples,
each keyed to the normative rule it exercises, with coverage reported so an untested rule or an
orphaned fixture doesn't hide. Run the retained verdicts and verify that the generated coverage
report is current:

```bash
python3 tools/run_corpus.py --check
```

A green run is the conformance gate — it is what "implements Whyspec" means here, not a claim
anyone has to take on faith.

## Why this is open when the product is not

Attrica is a hosted service and is developed privately. The specification is deliberately not:
a format that records *why* decisions were made is worth little if reading it requires one
vendor's permission. Publishing the format means the records in your repository stay yours
and stay readable, by us, by you, or by a tool nobody has written yet.

## Reserved

The bare root filename `Whyfile` is **reserved and explicitly unclaimed**. A future index or
manifest may want the classic `Makefile` position, and reserving it costs a sentence where
retrofitting it would cost a migration. Do not assign it meaning.

Historical note: documents predating version 0.8 used "Whyfile" for a configuration artifact,
since retired and renamed `why.config.toml`. The term was then re-purposed to name a decision
record itself, capitalized in the style of `Makefile` or `Dockerfile` — and has since been
retired again: this specification and project are now **Whyspec**, and a record is a **why
record**, lowercase and generic. "Whyfile" survives only as the literal reserved filename above,
and in documents written under either earlier sense.

## Status

Draft. The specification is being extracted from the reference implementation and is not yet
stable. Nothing here should be treated as frozen until a version is tagged.

## License

Specification text and fixtures are licensed under Apache-2.0 — see [LICENSE](LICENSE) and
[NOTICE](NOTICE). The **name** "WhyDB", the name "whyfile", and the phrase
"whyfile-compatible" are trademarks of Four Birds Limited and are not licensed by
Apache-2.0; see [TRADEMARKS.md](TRADEMARKS.md).

Contributions require a Developer Certificate of Origin sign-off — see
[CONTRIBUTING.md](CONTRIBUTING.md).
