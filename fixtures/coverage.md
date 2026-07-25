# B2 fixture coverage table

Rule id -> one-line statement -> valid fixture(s) -> invalid fixture(s). Generated from
`manifest.json`; every rule below has at least one valid fixture, and every rule below
either has at least one invalid fixture or an explicit note explaining why none exists
(see the **No orphan rules** and **No orphan fixtures** checks at the bottom).

## REC -- Record format -- what makes a markdown file a decision record, and how its fields parse.

| Rule | Statement | Valid fixture(s) | Invalid fixture(s) |
|---|---|---|---|
| **REC-001** | A record's H1 MUST be `# ADR-<digits><sep><title>` (sep in em-dash/en-dash/colon/hyphen) or `# Decision: <title>`; any other H1 means the file is NOT a decision record. | `records/REC-001-valid-adr-h1.md`<br>`records/REC-001-valid-decision-h1.md` | `records/REC-001-invalid-no-record-h1.md` |
| **REC-002** | A record MUST have a `## Decision` section (case-insensitive heading); its body becomes the rationale. Without it the file is not a record, even if the H1 gate passes. | `records/REC-001-valid-adr-h1.md` | `records/REC-002-invalid-missing-decision-section.md` |
| **REC-003** | A BOM (U+FEFF) is stripped only when it is the very FIRST character of the file. A BOM occurring elsewhere (e.g. immediately before a later heading) is left in place and is NOT treated as part of the heading gate. | `records/REC-003-valid-leading-bom.md` | `records/REC-003-invalid-non-leading-bom-breaks-heading.md` |
| **REC-004** | `## Alternatives considered` (or `## Alternatives`) is OPTIONAL; when absent, `alternatives` MUST be an empty list, not an error. | `records/REC-004-valid-no-alternatives-section.md` | _none -- no meaningful invalid example -- an absent Alternatives section is documented degrade-to-`[]` behaviour, not an error; every input is accepted, so there is nothing to reject. This is a SHOULD-shaped rule, not a MUST-reject one._ |
| **REC-005** | Alternatives are parsed as a FLAT top-level list only (numbered `1.`/`2.` or bulleted `-`/`*`). Nested/indented sub-bullets are NOT attached to their parent item; each becomes its own separate flat list item. | `records/REC-001-valid-adr-h1.md` | `records/REC-005-invalid-nested-bullets-flatten-unexpectedly.md` |
| **REC-006** | Status comes from the inline `**Status:**` line when present; normalised to the first lowercase alphabetic word (tolerating trailing punctuation/clauses). A `## Status` section heading is used ONLY as a fallback when no inline `**Status:**` line exists -- if both are present, the inline line always wins. | `records/REC-006-valid-inline-status.md`<br>`records/REC-006-valid-status-section-heading.md`<br>`records/REC-006-valid-status-with-trailing-clause.md` | `records/REC-006-invalid-inline-status-wins-over-section.md` |
| **REC-007** | A record whose normalised status is 'rejected' MUST be excluded from the authored/captured ground-truth node set built from a directory of records -- the option not taken must never become ground truth. | `dirs/REC-007-rejected-excluded/` | `dirs/REC-007-rejected-excluded/` |
| **REC-008** | A `## Assumptions` list item MAY carry a `(review by YYYY-MM-DD)` clause and/or an `(expires: ...)` clause, both stripped from the claim text into separate `review_by`/`expiry` fields. A review-by date that is not in YYYY-MM-DD form is NOT extracted -- it stays embedded in the claim text. | `records/REC-008-valid-assumptions-review-by-and-expiry.md` | `records/REC-008-invalid-malformed-review-by-date-not-extracted.md` |
| **REC-009** | An ADR H1's `ADR-<digits>` prefix and its separator are stripped from the parsed title; the title is the H1 text with that prefix removed, not the raw heading. | `records/REC-001-valid-adr-h1.md` | _none -- no meaningful invalid example -- prefix-stripping is a deterministic string transform with no reject branch (every ADR-shaped H1 has exactly one correct stripped title)._ |
| **REC-010** | A `## Recommendation` section produces a `resolution_delta: {recommended, chosen}` field on the node ONLY when its text differs from the chosen/title text. When it is absent, or textually equal to the title, `resolution_delta` MUST be omitted entirely (never emitted as null/empty). | `records/REC-010-valid-recommendation-differs-resolution-delta.md` | `records/REC-010-invalid-recommendation-equals-chosen-no-delta.md` |
| **REC-011** | Supersession is recorded ONLY for the ACTIVE phrasing `supersedes ADR-<digits>` found anywhere in the record text. The passive phrasing `superseded by ADR-<digits>` MUST NOT be captured as an outgoing `supersedes` reference. | `records/REC-011-valid-active-supersedes.md` | `records/REC-011-invalid-passive-superseded-by-is-not-active-supersession.md` |

## VER -- Versioning / filename scheme -- how a captured record's filename is chosen and matched over time.

| Rule | Statement | Valid fixture(s) | Invalid fixture(s) |
|---|---|---|---|
| **VER-001** | A brand-new captured record is named `YYYY-MM-DD-<question-slug>.md`. The slug MUST derive from the QUESTION text, never from the chosen option. | `filenames/VER-001-valid-new-dated-from-question.json` | `filenames/VER-001-invalid-slug-from-chosen-not-question.json` |
| **VER-002** | Re-capturing the SAME question on a later date MUST reuse the existing dated record file (whatever its own date), never create a second one. Reuse requires a well-formed 4-2-2 all-digit date prefix; a malformed prefix does not count as an existing dated record. | `filenames/VER-002-valid-idempotent-reuse-across-dates.json` | `filenames/VER-002-invalid-malformed-date-prefix-not-reused.json` |
| **VER-003** | A pre-dated-scheme (legacy) filename `<chosen-slug>.md` is reused ONLY when the file's recorded `## Context` body matches the new question (whitespace/case-normalised). A legacy file recording a DIFFERENT question, even with an identical chosen-derived filename, MUST NOT be reused/overwritten. | `filenames/VER-003-valid-legacy-reused-when-context-matches.json` | `filenames/VER-003-invalid-legacy-not-stolen-when-context-differs.json` |
| **VER-004** | A legacy-named file that cannot be recognised as a decision record at all (no parseable `## Context` section) MUST NEVER be treated as a match, regardless of filename. | `filenames/VER-003-valid-legacy-reused-when-context-matches.json` | `filenames/VER-004-invalid-unreadable-legacy-never-claimed.json` |
| **VER-005** | The lookup for an existing dated record MUST use a digit-CLASS-anchored glob (`[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-<qslug>.md`), never an unanchored `*`-prefixed pattern -- `*` can match a short question's slug as a mere suffix of an unrelated, longer, older record's slug. | `filenames/VER-005-valid-anchored-glob-matches-own-file.json` | `filenames/VER-005-invalid-unanchored-star-glob-suffix-collision.json` |
| **VER-006** | The digit-CLASS-anchored glob must also beat a `?`-positional pattern (`????-??-??-<qslug>.md`): `?` matches ANY character, not only digits, so it can mistake a legacy undated filename for a dated one when the legacy slug happens to be 'date-shaped' in its first 11 characters. | `filenames/VER-006-valid-anchored-glob-real-dated-prefix.json` | `filenames/VER-006-invalid-question-glob-digit-costume-collision.json` |
| **VER-007** | A new-scheme (question-derived) slug longer than 60 characters is truncated at a WORD boundary, never mid-word. (The separate LEGACY slug function intentionally hard-cuts at exactly 60 chars and must never be changed to match -- it exists only to reproduce old filenames byte-for-byte.) | `filenames/VER-007-valid-word-boundary-truncation.json` | `filenames/VER-007-invalid-mid-word-truncation.json` |

## PROV -- Provenance -- the trust-tier vocabulary and how it ranks/aggregates.

| Rule | Statement | Valid fixture(s) | Invalid fixture(s) |
|---|---|---|---|
| **PROV-001** | Valid provenance tier values are exactly {authored, captured, attested, reconstructed}. Trust ranking, most to least trusted: authored < captured < attested < reconstructed (lower rank integer = more trusted). | `provenance/PROV-001-valid-rank-order.json` | `provenance/PROV-001-invalid-rank-order.json` |
| **PROV-002** | A record whose H1 is `# ADR-...` ingests with provenance='authored'; a record whose H1 is `# Decision: ...` ingests with provenance='captured'. The two MUST map to different tiers. | `provenance/PROV-002-valid-h1-kind-to-tier-mapping.json` | `provenance/PROV-002-invalid-swapped-tier-mapping.json` |
| **PROV-003** | A node with a missing/absent `provenance` key, an empty string, or any unrecognised value MUST rank/count identically to `reconstructed` (the lowest tier) -- never silently promoted to a trusted tier. | `provenance/PROV-003-valid-absent-defaults-to-reconstructed.json` | `provenance/PROV-003-invalid-absent-treated-as-authored.json` |
| **PROV-004** | golden_fraction counts only nodes whose provenance is in {authored, captured, attested}; reconstructed (and absent-provenance) nodes never contribute to the golden numerator under any circumstance. An empty node list yields 0%, not an error. | `provenance/PROV-004-valid-golden-fraction.json` | `provenance/PROV-004-invalid-golden-fraction-blends-reconstructed.json` |

## ENV -- Result envelope -- the per-command JSON shape returned by the CLI.

| Rule | Statement | Valid fixture(s) | Invalid fixture(s) |
|---|---|---|---|
| **ENV-001** | Every command's JSON envelope MUST include a `command` key (the subcommand name) and a `status` key. These are the ONLY two keys guaranteed common to every command -- the envelope is a per-command tagged union, not one fixed shape. | `envelopes/ENV-002-valid-why.json` | `envelopes/ENV-001-invalid-missing-status.json` |
| **ENV-002** | The `why` command's envelope keys are EXACTLY {command, count, cutoff, query, results, score_stats, status} -- no more, no fewer. | `envelopes/ENV-002-valid-why.json` | `envelopes/ENV-002-invalid-why-missing-score-stats.json` |
| **ENV-003** | The `list-intent` command's envelope keys are EXACTLY {command, count, filter, intent, status}. | `envelopes/ENV-003-valid-list-intent.json` | `envelopes/ENV-003-invalid-list-intent-missing-filter.json` |
| **ENV-004** | The `coverage` command's envelope keys are EXACTLY {command, status, authored_anchored_files, authored_anchored_symbols, code_files, code_symbols, dark_files, file_coverage_pct, files_with_intent, golden, intent_by_kind, intent_debt, symbol_coverage_pct, symbols_with_intent} (14 keys total). | `envelopes/ENV-004-valid-coverage.json` | `envelopes/ENV-004-invalid-coverage-missing-golden.json` |
| **ENV-005** | The `check` command's envelope keys are EXACTLY {command, status, rules, files_checked, violations}. | `envelopes/ENV-005-valid-check.json` | `envelopes/ENV-005-invalid-check-missing-violations.json` |
| **ENV-006** | `graph_identity` is NEVER part of the CLI's JSON envelope for any command. It is attached only by the MCP transport layer (mcp_server.py), and its presence or absence must never be used to satisfy or substitute for a command's real required-key set. | `envelopes/ENV-003-valid-list-intent.json` | `envelopes/ENV-006-invalid-graph-identity-not-a-substitute-for-required-field.json` |

## No orphan rules / no orphan fixtures

- Rules defined: 28. Rules with zero fixtures (orphan rules): none.
- Fixtures citing a rule id not in the inventory above (orphan fixtures): none.
- Rules with a valid fixture but no invalid fixture and no documented reason (should be empty): none.
- Rules with no valid fixture at all (should be empty): none.

