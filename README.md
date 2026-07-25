# The Whyfile specification

The open specification behind **WhyDB** — *Why this, not that.*

A **Whyfile** is a decision record: a markdown file, in your own repository, that says what
was decided, what the alternatives were, and why one was chosen. Capitalized like
`Makefile` or `Dockerfile` — "a Whyfile", plural "Whyfiles" — conventionally kept under
`docs/decisions/`. The lowercase `whyfile` is the command and package name, following the
same convention as `docker` and `Dockerfile`.

This repository specifies three things, and nothing else:

- **the record format** — how a Whyfile is written and parsed
- **the result envelope** — the shape of an answer to a query
- **the provenance vocabulary** — the tiers a claim can come from, and what each is worth

It also carries a machine-checkable `fixtures/` corpus: valid and invalid examples for every
normative rule, so a conforming implementation can be verified rather than asserted.

## Why this is open when the product is not

WhyDB is a hosted service and is developed privately. The specification is deliberately not:
a format that records *why* decisions were made is worth little if reading it requires one
vendor's permission. Publishing the format means the records in your repository stay yours
and stay readable, by us, by you, or by a tool nobody has written yet.

## Reserved

The bare root filename `Whyfile` is **reserved and explicitly unclaimed**. A future index or
manifest may want the classic `Makefile` position, and reserving it costs a sentence where
retrofitting it would cost a migration. Do not assign it meaning.

Historical note: documents predating version 0.8 used "Whyfile" for a configuration
artifact, since retired and renamed `whyfile.config.json`. The term has been re-purposed;
it is not continuous with that earlier use.

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
