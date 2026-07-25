# The Whyfile Format Specification

**Version:** 0.1 — working draft
**Status:** Draft. Not frozen. Not a standard. Rule ids are stable within this draft and are
referenced by the conformance corpus; rule *text* may still change.

---

## 1. Preface

### 1.1 What this document is

This is the normative description of the **Whyfile format**: a plain-markdown record of a
decision — what was chosen, what else was on the table, and why — that lives in the repository
whose code the decision governs.

The format exists because the reasoning behind code is the part that does not survive. Diffs
survive, tests survive, the argument that produced them does not. A Whyfile makes that argument a
file: greppable, reviewable, diffable, and mechanically ingestible into a queryable decision
layer.

This document specifies three things and only three:

1. **The record format** — how a Whyfile is written and how a conforming parser reads it.
2. **The result envelope** — the shape of a JSON answer returned by a query over records.
3. **The provenance vocabulary** — the trust tiers a piece of recorded intent can carry, and their
   ordering.

### 1.2 Conventions

The key words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are to be
interpreted as described in RFC 2119.

Every normative statement carries a stable identifier in one of four families:

| Family | Governs |
|---|---|
| `REC-nnn` | Record format — syntax, sections, filenames, identity |
| `PROV-nnn` | Provenance vocabulary — tiers, ordering, trust semantics |
| `ENV-nnn` | Result envelope — the JSON shape of a query answer |
| `VER-nnn` | Versioning policy — when a change requires a version marker |

A complete index of every rule id appears in §9.

### 1.3 Scope

In scope:

- The on-disk syntax of a decision record, and the deterministic rules for parsing one.
- Which fields a parsed record yields, and which are optional.
- Filename derivation, and the compatibility rules that keep an existing record's identity stable.
- The provenance tiers and their total order.
- The JSON envelope a query returns.
- The rule that governs when a format change requires a version marker.

### 1.4 Non-goals

The following are deliberately **not** specified here. A format specification that pins an
implementation stops being implementable by anyone else, and each item below is a place where
implementations should be free to differ.

- **Storage.** Whether records are read from a working tree, a git object database, an index, a
  cache, or a network service. The format says what a record *is*, not where it lives.
- **Transport.** How a query reaches an implementation or how an answer is returned — process
  invocation, HTTP, a tool-call protocol, a library call. §6.6 draws the line between the
  spec-governed envelope and whatever a transport wraps around it.
- **Ranking and retrieval.** How an implementation scores a free-text question against a corpus of
  records. The envelope reserves fields for scores and match evidence (§6.5.1) and constrains their
  *meaning*, not their computation. Two conforming implementations may legitimately return
  different results for the same question.
- **Product behaviour.** Capture workflows, review surfaces, linting, gating, notification,
  authorization, or any policy about what a consumer should *do* with a record.
- **Extraction of intent from non-record sources.** The `reconstructed` and `attested` provenance
  tiers (§5) are named here because the ordering is not meaningful without them, but how an
  implementation derives such intent is out of scope.
- **Conformance levels, profiles, or feature negotiation.** There is one format. An implementation
  either parses it as specified or does not.

---

## 2. Terminology

**Whyfile** (capitalized, one word) — a decision record in this format. Capitalized like
`Makefile` or `Dockerfile`. Plural **Whyfiles**. Conventionally stored under `docs/decisions/`.

**whyfile** (lowercase) — the command and package name. When this document says "whyfile", it
means the tool; when it says "a Whyfile", it means a record.

**WhyDB** — the brand. *Why this, not that.*

**Record** — a Whyfile. Used interchangeably.

**Record kind** — one of the two forms a record may take: an **ADR record** or a **decision
record** (§4.1).

**Intent node** — the structured object a parsed record becomes when ingested into a queryable
decision layer. The format specifies the parse; the node is what a query answers with.

**Provenance tier** — the trust class of a piece of intent (§5).

**Envelope** — the top-level JSON object a query returns (§6).

### 2.1 The bare root filename `Whyfile` is reserved

**[REC-001]** The bare, extensionless filename `Whyfile` at a repository root is **RESERVED** by
this specification and is **explicitly unclaimed**. An implementation **MUST NOT** assign it a
meaning, and a repository **SHOULD NOT** create a file with that name expecting any implementation
to read it.

The reservation is forward-looking. A future index, manifest, or repository-level contract may
want the classic `Makefile` position at the root, and that position is only available if nothing
has quietly taken it first. Reserving it costs one sentence now; retrofitting it later costs a
migration in every adopting repository.

### 2.2 Historical note: the term was re-purposed

Documents predating the 0.8 line use "Whyfile" to name a **configuration artifact** — a
repository's checked-in tool contract — rather than a decision record. That artifact was renamed
to `whyfile.config.json`, and the bare capitalized name it briefly held was retired.

The term was therefore **re-purposed, not continuous**. "Whyfile" in this specification always
means a decision record. A reader encountering the older sense in an archived document is looking
at a different thing that happened to share a name.

---

## 3. Document model

### 3.1 Encoding and lexical rules

**[REC-002]** A record **MUST** be a UTF-8 encoded markdown document.

**[REC-003]** A parser **MUST** tolerate a leading UTF-8 byte-order mark (U+FEFF) and **MUST NOT**
let its presence change the parse.

**[REC-004]** A parser **MUST** treat a line matching `^(#{1,6})\s+(.+)$` as a heading, where the
count of `#` characters is the heading level and the remainder, trimmed, is the heading text. A
section's **body** is all text from the end of its heading line to the start of the next heading of
any level, trimmed.

**[REC-005]** Heading text **MUST** be matched case-insensitively when a parser is deciding which
section a heading names.

> **Known gap — fenced code blocks are not excluded.** The reference implementation matches
> headings and the inline status line (§4.6) over the raw document text, without excluding fenced
> code blocks. A `## Decision` heading or a `**Status:** Rejected` line inside a fenced block is
> read as though it were structural. This is a genuine hazard: a record demonstrating record syntax
> inside a code fence can silently change its own parse, and a status of `rejected` causes the
> record to be excluded from ingest entirely (§4.6). Implementers should be aware of it; this
> document does not invent a rule to close it. See §8, gap G1.

### 3.2 What is not read

**[REC-006]** YAML front matter, if present, **MUST NOT** be interpreted by a conforming parser.
Front matter is human and external-tooling metadata. A record's meaning **MUST** be fully
determined by its markdown body.

**[REC-007]** A parser **MUST NOT** require any section not named in §4. Unrecognized sections
**MUST** be ignored without error. This is what makes §7's vocabulary-extension rule safe.

---

## 4. Record format

### 4.1 The two record kinds

**[REC-008]** A markdown document is a record **if and only if** both of the following hold:

1. It contains a level-1 heading matching one of exactly two forms (§4.2, §4.3), and
2. it contains a `Decision` section (§4.5).

A document failing either condition **MUST NOT** be treated as a record. This is what allows a
template, a README, or an unrelated document to sit in the same directory without being ingested.

**[REC-009]** The record kind is determined by which level-1 form matched:

| H1 form | Kind | Provenance tier |
|---|---|---|
| `# ADR-<digits><sep> <title>` | `adr` | `authored` (§5) |
| `# Decision: <title>` | `decision` | `captured` (§5) |

**[REC-010]** A parser **MUST** use the **first** level-1 heading that matches either form as the
record's title heading, and **MUST** ignore any later level-1 heading. A level-1 heading that
matches neither form **MUST NOT** disqualify the document: the parser continues looking.

> This is verified behaviour, not an inference. A document whose first H1 is `# Notes` and whose
> second is `# Decision: A` parses as a decision record titled `A`.

### 4.2 ADR heading grammar

**[REC-011]** An ADR heading **MUST** match, case-insensitively:

```
ADR-<one or more digits><optional whitespace><separator><optional whitespace><title>
```

where `<separator>` is exactly one of: em dash `—` (U+2014), en dash `–` (U+2013), colon `:`, or
hyphen-minus `-`.

**[REC-012]** The separator is **REQUIRED**. `# ADR-0007 Title` — digits followed by whitespace and
a title with no separator — is **NOT** an ADR heading and the document **MUST NOT** be treated as an
ADR record on the strength of it.

**[REC-013]** The digit run **MUST NOT** be required to be zero-padded or of any fixed width for
*heading recognition*. `# ADR-7: Title` is a valid ADR heading. Note that ADR *number resolution*
for supersession (§4.8) reads the filename, not the heading, and has a different rule.

### 4.3 Decision heading grammar

**[REC-014]** A decision heading **MUST** match, case-insensitively:

```
Decision:<optional whitespace><title>
```

### 4.4 Title

**[REC-015]** The record's **title** is the matched heading text with its prefix (the `ADR-…` run
and separator, or the `Decision:` literal) removed, and surrounding whitespace trimmed.

**[REC-016]** The title **MUST** be non-empty. A record whose title reduces to the empty string
**MUST NOT** be treated as a record.

**[REC-017]** For a `decision` record the title is, by construction, the **chosen option**. Emitters
**MUST** write the chosen option as the title (§4.10), and consumers **MAY** rely on this: it is
what `resolution_delta` (§4.9) compares a recommendation against.

### 4.5 Sections

**[REC-018]** A parser **MUST** recognize the following section headings, matched
case-insensitively against the full trimmed heading text:

| Heading | Required | Yields |
|---|---|---|
| `Decision` | **yes** | `rationale` — the section body, trimmed |
| `Context` | no | see [REC-021] |
| `Alternatives considered` *or* `Alternatives` | no | `alternatives` — an ordered list of strings |
| `Recommendation` | no | `recommendation` — the section body, trimmed |
| `Assumptions` | no | `assumptions` — a list of structured claims (§4.7) |
| `Status` | no | fallback status source (§4.6) |

**[REC-019]** When more than one section matches the `Decision` heading, the parser **MUST** use the
**first** and ignore the rest. The same first-wins rule applies to every heading in the table.

**[REC-020]** Records **SHOULD** write all sections in [REC-018] at heading level 2.

> **Divergence flagged.** The reference implementation applies no level constraint to section
> headings: `### Decision` and `###### Decision` are both accepted as the Decision section (verified
> by execution). Only the *title* heading is level-constrained. [REC-020] is therefore a SHOULD on
> emitters, deliberately not a MUST on parsers — tightening parsers to level 2 would reject records
> already in the field. Recommend the engine keep its permissive parse and that the corpus fix the
> emitted level at 2. See §8, gap G2.

**[REC-021]** The `Context` section carries the **question** the record answers. Emitters **MUST**
render it (§4.10). A parser **MAY** ignore it: the reference implementation does not surface it as a
parsed field, and it therefore does not reach the intent node.

> **Known gap.** This makes the question durable in the file but absent from the queryable layer,
> even though the question is the field the filename is derived from (§4.11) and the field used to
> decide whether an existing record is *this* decision. The asymmetry is real and unresolved; this
> document records it rather than inventing a parse rule. See §8, gap G3.

### 4.5.1 Alternatives

**[REC-022]** The alternatives section body **MUST** be parsed as a flat list. A list item begins at
a line matching `^[ \t]*(?:\d+\.|[-*])[ \t]+`; the item's text runs to the start of the next such
marker or the end of the section.

**[REC-023]** Each item's text **MUST** be normalized by collapsing all whitespace runs to a single
space, trimming, and removing every `**` sequence. Empty items **MUST** be dropped.

**[REC-024]** Alternatives **MUST** be yielded in document order.

**[REC-025]** A prose (list-free) alternatives section **MUST** yield an empty alternatives list,
not an error and not the prose.

**[REC-026]** Records **SHOULD NOT** nest list items under an alternative. Nesting carries no
meaning in this format: the reference implementation flattens every marker to a top-level item, so
a sub-bullet becomes an alternative in its own right.

### 4.6 Status

**[REC-027]** A record's status **MAY** be given in either of two forms:

- **Inline** — a line matching `^\s*\*\*status:?\*\*\s*:?\s*(.+?)\s*$`, case-insensitively. This
  tolerates `**Status:** X`, `**Status**: X`, and `**Status** : X`.
- **Section** — a `## Status` section, whose body supplies the value.

**[REC-028]** When both forms are present the **inline** form **MUST** win.

**[REC-029]** The inline form **MUST** be searched over the whole document, and the **first**
line-anchored match **MUST** win. It is not scoped to any section.

**[REC-030]** A status value **MUST** be normalized to its first run of lowercase alphabetic
characters. `Rejected in favor of ADR-9`, `: Rejected.`, and `REJECTED` all normalize to
`rejected`. A value containing no alphabetic characters normalizes to absent.

**[REC-031]** When no status can be determined, the parsed record's status **MUST** be absent. An
implementation **MUST NOT** substitute a default, and **MUST NOT** serialize an explicit null in
place of the field on the resulting intent node — the key is omitted entirely. See [ENV-026] for
the general absent-versus-null convention.

**[REC-032]** A record whose normalized status is `rejected` **MUST NOT** become ground-truth intent
of any tier, and its assumptions **MUST NOT** either. A rejected record is the option *not* taken;
ingesting it would invert its meaning.

**[REC-033]** No other status value is normative. `accepted`, `open`, `resolved`, `superseded`,
`proposed` and similar values are conventional; implementations **MUST NOT** attach behaviour to
them beyond [REC-032].

### 4.7 Assumptions

**[REC-034]** Each list item in the `Assumptions` section (parsed per [REC-022]–[REC-025]) **MUST**
yield one assumption with a `claim`, plus two optional fields.

**[REC-035]** An item **MAY** carry a review date matching, case-insensitively,
`\(?\s*review[ -]by:?\s*(\d{4}-\d{2}-\d{2})\s*\)?` — accepting `(review by 2027-01-31)` and
`(review-by: 2027-01-31)`. The captured date **MUST** be yielded as `review_by` and **MUST** be
removed from the claim text.

**[REC-036]** `review_by` **MUST** be a full ISO-8601 calendar date, `YYYY-MM-DD`. It is the
machine-checkable field: an implementation may compare it against the current date to surface an
assumption due for re-examination.

**[REC-037]** An item **MAY** carry an expiry condition matching, case-insensitively,
`\(\s*expires?:?\s*([^)]+?)\s*\)`. The captured text **MUST** be yielded as `expiry` and **MUST** be
removed from the claim text. `expiry` is **free text and not machine-checkable**; it records a
condition, not a date.

**[REC-038]** After both strippings, the claim **MUST** be normalized by collapsing whitespace and
trimming spaces and periods from both ends.

**[REC-039]** `review_by` and `expiry` **MUST** be omitted entirely when not present, not
serialized as null.

### 4.8 Supersession

**[REC-040]** A record declares supersession in prose. A parser **MUST** collect every match of
`\bsupersedes?\s+(ADR-\d+)`, case-insensitively, over the whole document.

**[REC-041]** The **passive** form — "superseded by ADR-N" — **MUST NOT** be read as a supersession
claim. A record's supersedes list names what *it* replaces, never what replaces it. The regex in
[REC-040] achieves this because `\bsupersedes?\s+ADR` cannot match across the intervening `by`.

**[REC-042]** Collected references **MUST** be uppercased, de-duplicated, and yielded in
first-seen order.

**[REC-043]** Resolving a reference to a target record **MUST** be done by the **ADR number in the
target's filename**, taken as the first run of exactly four digits. A candidate record whose
filename carries no such run **MUST NOT** be resolvable as a supersession target.

> Note the deliberate asymmetry with [REC-013]: heading recognition accepts any digit run, target
> resolution requires four digits in the filename. Both are the reference behaviour. An ADR whose
> heading is `# ADR-7: …` is a valid record but is not addressable as a supersession target unless
> its filename carries `0007`.

**[REC-044]** A supersession reference that resolves to no known record **MUST** be dropped
silently, not reported as a violation. Records are ingested from a directory that may be partial.

### 4.9 Resolution delta

**[REC-045]** When a record carries a `Recommendation` section whose trimmed body **differs** from
the record's trimmed title, the resulting intent node **MUST** carry a `resolution_delta` object:

```json
{ "recommended": "<recommendation body>", "chosen": "<title>" }
```

**[REC-046]** When the recommendation is absent, empty, or equal to the title, `resolution_delta`
**MUST** be omitted from the node entirely.

`resolution_delta` is the record of a human overriding a recommendation. It is the highest-signal
field in the format for anyone studying decision quality, precisely because it is the case where
the recommended answer and the chosen answer diverged and someone wrote both down.

> **Known gap.** `resolution_delta` is set on the intent node and is reported in the capture
> envelope (§6.5.9), but is **not** projected into any query result envelope by the reference
> implementation — not `why`, not `list-intent`, not `explain`. It is durable but not queryable.
> See §8, gap G4.

### 4.10 Canonical rendering

An emitter producing a `decision` record **MUST** produce exactly this shape. This is the
write-path half of the format; [REC-047]–[REC-053] make it round-trip with §4.1–§4.9 by
construction.

```markdown
# Decision: <chosen>

**Status:** <status>
**Date:** <YYYY-MM-DD>

## Context

<question, or "(none recorded)">

## Decision

<rationale, or <chosen> when the rationale is empty>

## Alternatives considered

1. <option>
2. <option>

## Recommendation

<recommendation>
```

**[REC-047]** The `**Status:**` and `**Date:**` lines **MUST** be emitted on adjacent lines
immediately after a single blank line following the H1, with no blank line between them.

**[REC-048]** Section order **MUST** be: `Context`, `Decision`, `Alternatives considered`, then
`Recommendation`.

**[REC-049]** The `Recommendation` section **MUST** be emitted only when a non-empty recommendation
was supplied, and **MUST** be omitted entirely otherwise.

**[REC-050]** When no question was supplied, the `Context` body **MUST** be the literal
`(none recorded)`. When no alternatives were supplied, the `Alternatives considered` body **MUST**
be the literal `(none recorded)`.

**[REC-051]** When the rationale is empty, the `Decision` body **MUST** be the chosen option (the
title). A record must never be emitted without a Decision section, because a record without one is
not a record ([REC-008]).

**[REC-052]** Alternatives **MUST** be emitted as a flat, one-based, `N. ` numbered list in the
order supplied.

**[REC-053]** The document **MUST** end with a single trailing newline.

#### 4.10.1 The placeholder rule

**[REC-054]** A `(none recorded)` placeholder **MUST** be emitted only for a section where the
absence of content is itself an answer — "we considered the question and there was nothing to
list". It **MUST NOT** be emitted for a section whose absence means "nobody was asked".

This distinction is normative, not stylistic. `## Alternatives considered` with `(none recorded)`
honestly says *we looked and there were none*. A section rendered the same way for evidence,
provenance, or any other field a human may simply never have been prompted for would state a false
claim about the record's own completeness. A record must not lie about what it knows about itself.

**[REC-055]** Accordingly, an optional section added by a future vocabulary extension (§7)
**MUST** be omitted entirely when it has no content, unless [REC-054]'s first condition applies to
it.

### 4.11 Filenames

**[REC-056]** A record's filename **SHOULD** be `YYYY-MM-DD-<question-slug>.md`, where the date is
the UTC calendar date of capture and the slug derives from the **question**, not the chosen option
([REC-058]).

The dated form is sortable, greppable, and — critically — collision-safe. The slug derives from the
question because *the question is what makes a decision unique*. Chosen text repeats constantly:
"document only", "keep it", "defer" are answers to entirely unrelated questions. Under a
chosen-derived naming scheme, two captures answering different questions with the same words
silently overwrote each other's record. That was a data-loss defect wearing a papercut's clothes,
and it is the reason this rule exists. Any implementation tempted to "simplify" the naming scheme
back to the chosen option will reintroduce it.

**[REC-057]** Records **SHOULD** live under `docs/decisions/`; ADR records **SHOULD** live under
`docs/adr/`. Neither location is normative — an implementation **MUST** accept records from any
directory it is pointed at, and **MUST NOT** infer a record's kind from its directory. Kind comes
from the H1 ([REC-009]) and nothing else.

#### 4.11.1 Slug derivation

**[REC-058]** A slug **MUST** be derived from its source text by:

1. lowercasing;
2. replacing every run of characters outside `[a-z0-9]` with a single `-`;
3. stripping leading and trailing `-`.

**[REC-059]** A slug **MUST** be bounded at 60 characters.

**[REC-060]** Truncation **MUST** land on a word boundary: truncate to the bound, then, if the
result contains a `-`, drop everything from the last `-` onward, then strip trailing `-`.

> Hard-cutting mid-word produced records ending in fragments — `…existing-error-classe.md` — which
> read as permanent typos in a directory humans scan by eye. The word-boundary rule is cosmetic in
> effect and load-bearing in adoption.

**[REC-061]** If the first word alone exceeds the bound, the slug **MUST** be hard-cut. A slug must
be bounded; this is the only case where a mid-word cut is permitted.

**[REC-062]** A slug that reduces to the empty string **MUST** become the literal `decision`.

**[REC-063]** Because slug output is restricted to `[a-z0-9-]` by [REC-058], a slug **MUST NOT** be
able to contain a glob metacharacter. Implementations **MAY** rely on this when constructing the
pattern in [REC-067].

#### 4.11.2 Idempotency and legacy-name compatibility

Re-recording a decision must update *its* record, not fork a twin. An implementation **MUST**
resolve a record's destination by trying the following in order, and **MUST** use the first that
succeeds.

**[REC-064]** **Legacy name.** If a file named `<slug-of-chosen>.md` exists in the records
directory **and** its `## Context` section, whitespace-normalized and lowercased, equals the
whitespace-normalized, lowercased question, that file **MUST** be reused.

**[REC-065]** A legacy file **MUST NOT** be claimed on filename alone. Legacy names key on the
chosen option, which is exactly the field that collides; claiming on name alone perpetuates the
overwrite defect [REC-056] exists to kill. A file that cannot be read, or that has no recognizable
`## Context`, **MUST NOT** be claimed.

**[REC-066]** A question that is empty **MUST** be treated as matching a recorded context of
`(none recorded)`, and only that.

**[REC-067]** **Existing dated record.** Otherwise, if any file matching
`[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-<question-slug>.md` exists, the lexicographically first
such file **MUST** be reused — whatever its date. A decision re-recorded next week updates last
week's file rather than forking.

**[REC-068]** The date portion of the pattern in [REC-067] **MUST** be expressed with **digit
character classes**. Neither `*-<slug>.md` nor `????-??-??-<slug>.md` is acceptable.

> This is not pedantry; both weaker forms are known-broken. `*` matches any text, so `*-budget.md`
> matches `retry-budget.md` — the same overwrite class. `?` is narrower but still matches any
> non-separator character, so `????-??-??-budget.md` matches `drop-py-39-budget.md`, a plausible
> legacy (undated) record name: legacy records share the directory, are named from the chosen text
> with no date prefix, and decision prose is routinely digit-heavy. Only `[0-9]` rejects both.

**[REC-069]** **Fresh name.** Otherwise the destination **MUST** be
`<today>-<question-slug>.md`.

**[REC-070]** A record's filename **MUST NOT** be changed by an implementation once written. Node
identity derives from the record path ([REC-071]); renaming forks every node's identity and orphans
every reference to it. This is why legacy names are honoured indefinitely rather than migrated: the
rename is the expensive operation, not the naming scheme.

### 4.12 Node identity

**[REC-071]** An intent node's identity **MUST** be derived from exactly four inputs, joined by
`::` in this order, and hashed:

```
<canonical source path> :: <source location> :: <intent kind> :: <normalized label>
```

For a decision node, source location and label are both the record title, and intent kind is
`decision`. For an assumption node they are derived from the claim, and the kind is `assumption`.

**[REC-072]** The **normalized label** **MUST** be the label lowercased, with every run of
characters outside `[a-z0-9]` replaced by `_`, and leading/trailing `_` stripped.

**[REC-073]** The **canonical source path** **MUST** be the repository-relative path in POSIX
separator form. An absolute path **MUST** be resolved (collapsing symlink aliases) and made relative
to the repository root before hashing. A path already relative **MUST** be left byte-identical apart
from separator normalization.

**[REC-074]** A path outside any repository **MUST** fall back to a POSIX-normalized absolute
spelling. Path canonicalization **MUST NOT** raise.

[REC-073] is what makes an identity reproducible across clones and across surfaces. Hashing an
absolute spelling makes every node id machine-specific: the same record ingested by a client that
happens to pass an absolute path forks the node that a repository-relative re-ingest produces, and
every reference to the original silently dangles.

---

## 5. Provenance vocabulary

Provenance is the format's **primary trust axis**. It answers "how do we know this?", and it is the
field a consumer must consult before treating recorded intent as ground truth.

### 5.1 The tiers

**[PROV-001]** Provenance **MUST** be one of exactly four values. The set is closed; an
implementation **MUST NOT** mint a fifth without a version marker (§7, [VER-003]).

| Tier | What it means | What it is worth |
|---|---|---|
| `authored` | Ingested verbatim from a **reviewed, ratified** human decision record — an ADR. | Ground truth. The strongest claim the format can carry: a human wrote it *and* a review process accepted it. |
| `captured` | Ingested verbatim from a decision record written **at the moment of choosing**. | Ground truth, human-written, but not yet reviewed or ratified. Highest-fidelity provenance available, because it was recorded when the reasoning was still in someone's head — but it carries one person's word, not a process's. |
| `attested` | Human rationale written as an **aside** — a commit trailer, an inline `# why:` comment, a pull-request body. | Human-written and bound to a specific diff, so it outranks anything inferred. Less formal than a record: it was never structured as a decision, so it rarely names alternatives. This is the zero-workflow tier every repository already has on day one. |
| `reconstructed` | **Inferred** from code or documentation by an automated pass. | The weakest tier. Plausible, useful for navigation, and never evidence. A consumer **MUST NOT** present reconstructed intent as something a human decided. |

### 5.2 Ordering

**[PROV-002]** The tiers **MUST** be totally ordered, highest trust first:

```
authored  >  captured  >  attested  >  reconstructed
```

**[PROV-003]** Intent with **absent or unrecognized** provenance **MUST** be ranked as
`reconstructed`.

The absent-default is deliberately the *weakest* tier, and the direction matters. Defaulting an
unknown to a strong tier would silently promote unlabelled data into ground truth; defaulting to the
weakest is the only safe failure. It is also what lets data written before the vocabulary existed
remain readable without a migration.

**[PROV-004]** When results are ordered by trust, provenance **MUST** be the primary sort key and
any numeric confidence the secondary key. An implementation **MUST NOT** allow a high-confidence
`reconstructed` result to outrank an `authored` one.

### 5.3 Assignment

**[PROV-005]** An ADR record ([REC-009]) **MUST** yield `authored` intent.

**[PROV-006]** A decision record ([REC-009]) **MUST** yield `captured` intent.

**[PROV-007]** An assumption node **SHOULD** inherit the provenance tier of the record that
declared it.

> **Divergence flagged — engine inconsistency.** The reference implementation mints **every**
> assumption node as `authored`, regardless of its record's kind (verified by execution: a
> `captured` record's assumption is created with provenance `authored`). The consequence is a trust
> inversion — an assumption outranks the decision that stated it, and unreviewed assumptions are
> counted as reviewed ground truth. [PROV-007] specifies what should be. See §8, gap G5, and §10.

**[PROV-008]** Intent ingested from a record **MUST** carry a numeric confidence of `1.0`. The
record *is* the evidence; there is nothing to be uncertain about at ingest.

**[PROV-009]** An implementation **MUST NOT** conflate provenance with a numeric confidence score
or with any string confidence label from an extraction pipeline. They are orthogonal axes:
provenance says *who said it*, confidence says *how sure the extractor was*. Filtering and merging
**MUST** use the numeric score only; trust decisions **MUST** use provenance only.

### 5.4 Trusted evidence classes

**[PROV-010]** The **golden tiers** — the evidence classes that count as trusted — **MUST** be
exactly `{authored, captured, attested}`.

**[PROV-011]** `reconstructed` intent **MUST NOT** be counted toward any trusted-evidence metric.

**[PROV-012]** A trust metric **MUST NOT** blend tiers into a single scalar without also reporting
the per-tier breakdown. A blended number is the one output that makes a corpus of inferences look
like a corpus of decisions.

---

## 6. Result envelope

### 6.1 Shape

**[ENV-001]** A query result **MUST** be a single JSON object. Not an array, not a stream of
objects, not a bare value.

**[ENV-002]** Every envelope **MUST** carry a `command` key: a stable lowercase string naming the
operation that produced it.

**[ENV-003]** Every envelope **MUST** carry a `status` key: a lowercase `snake_case` token
classifying the outcome.

**[ENV-004]** `command` and `status` are the **only** universal keys. A consumer **MUST NOT** assume
any other key is present without first dispatching on `command`.

This is the single most important rule in §6, and it is easy to get wrong by inspection of one
command. Field-verified top-level key sets.

A variant's key set is **not** unconditional: a status value may add a key. `why` is the
worked case — it carries an eighth key, `note`, exactly when `status` is `topically_weak`.
A conforming consumer must therefore treat a variant's key set as *keyed on the status it
carries*, and an implementation must not assert an exact key count for a variant without
naming the status it holds for.

| `command` | Top-level keys |
|---|---|
| `why` | `command`, `status`, `query`, `count`, `cutoff`, `score_stats`, `results`, and `note` **when and only when** `status` is `topically_weak` |
| `list-intent` | `command`, `status`, `count`, `filter`, `intent` |
| `explain` (ok) | `command`, `status`, `query`, `resolved`, `intent`, `explains`, `relations` |
| `explain` (ambiguous) | `command`, `status`, `query`, `candidates`, `message` |
| `explain` (not_found) | `command`, `status`, `query`, `message` |
| `changed` | `command`, `status`, `base`, `changed_files`, `files_with_intent`, `results` |
| `digest` | `command`, `status`, `since`, `added`, `removed`, `superseded` |
| `coverage` | `command`, `status` + 12 coverage-specific keys |
| `coverage` (explain form) | `command`, `status`, `explain`, `trace_present`, `referencing_intent`, `counts` |
| `check` | `command`, `status`, `rules`, `files_checked`, `violations` |
| `intent-diff` | `command`, `status`, `base`, `summary`, `introduces`, `supersedes`, `governed`, `constraint_review` |
| `review-context` | `command`, `status`, `base`, `changed_files`, `governing`, `unresolved_constraints`, `guidance` |
| `capture` | `command`, `status`, `record`, `record_abs`, `node_id`, `title`, `provenance`, `resolution_delta`, `merged` |

Not even `count` is universal — it appears on `why` and `list-intent` and nowhere else.

### 6.2 The envelope is a tagged union

**[ENV-005]** The envelope **MUST** be modelled as a **tagged union discriminated by `command`**,
over a small universal core of `{command, status}`. An implementation **MUST NOT** model it as one
struct with many optional fields.

The distinction has teeth. A one-struct model makes every command's fields optional on every other
command, which means a consumer cannot tell "this command does not have that field" from "this
command has it and it was null this time" — and a type system cannot help. A tagged union makes the
first case a compile error and the second a real value.

**[ENV-006]** Where a single `command` value carries more than one disjoint shape, the spec **MUST**
name the secondary discriminator explicitly, and a consumer **MUST** apply it before reading any
variant-specific key. Two such cases exist:

- **`coverage`** — two disjoint shapes share the tag. The discriminator is the presence of the
  `explain` key: present means the per-file explanation variant, absent means the corpus-wide
  summary variant. They share no keys beyond `command` and `status`.
- **`explain`** — three disjoint shapes keyed by `status` (`ok` / `ambiguous` / `not_found`).

> **Flagged for the engine.** `coverage` overloading one `command` tag with two unrelated payloads
> is the weakest point in the union. A `command` value of `coverage-explain` would make the
> discriminator primary and the union flat. This is a spec-level recommendation, not a rule, because
> changing it is a meaning change under §7 ([VER-001]) and needs its own decision. See §10.

### 6.3 Status

**[ENV-007]** Status tokens are **per-command**, not global. The following are the tokens the
reference implementation emits.

| `command` | Status tokens |
|---|---|
| `why` | `ok`, `weak_match`, `topically_weak`, `no_strong_match` |
| `explain` | `ok`, `ambiguous`, `not_found` |
| `list-intent` | `ok` |
| `changed` | `ok`, `no_intent_governing_changes` |
| `coverage` | `ok` (summary form); `ok`, `no_references` (explain form) |
| `digest` | `ok`, `no_changes` |
| `check` | `ok`, `conformance_failed` |
| `intent-diff` | `ok`, `conformance_required` |
| `review-context` | `ok`, `no_intent_governing_changes` |
| `capture` | `ok`, `dry_run`, `error` |
| any (input failure) | `no_intent_layer`, `error` |

**[ENV-008]** A consumer encountering an **unrecognized** status token **MUST** treat it as a
failure. Failing open on an unknown status is the silent-success defect: a refusal an agent reads as
an answer. Enumerate the statuses that mean success; treat everything else, including anything added
later, as an error.

**[ENV-009]** A status **MUST NOT** be overloaded to carry data. `ok` means the command completed
and its variant fields are populated; a distinct outcome gets a distinct token.

**[ENV-010]** A status that reports an honest negative — `no_changes`, `no_strong_match`,
`no_intent_governing_changes`, `no_references` — is a **complete answer**, not an error. An
implementation **MUST** distinguish "I looked and there is nothing" from "I could not look".

### 6.4 The error variant

**[ENV-011]** An envelope reporting a failure **MUST** carry `command`, `status`, and a human-
readable `message`. It **MUST NOT** be required to carry any variant-specific key.

**[ENV-012]** A consumer **MUST NOT** assume a variant-specific key is present merely because
`command` names a variant that normally has it. The error variant of every command is a legitimate
shape with none of them.

> **Flagged — engine inconsistency.** In the reference implementation, four failure paths on the
> tool-call transport emit an envelope with **no `command` key at all**: the wrong-repository
> refusal, the missing-graph refusal, the input-validation failure, and the internal-error catch.
> The same failures over the command-line surface *do* carry `command`. This breaks [ENV-002] — the
> one key the spec calls universal — on exactly the paths where a consumer most needs to know what
> it asked. The spec keeps [ENV-002] as a MUST and flags the engine. See §8, gap G6, and §10.

### 6.5 Command variants

Field lists below are normative for the variant they name. All are field-verified against the
reference implementation.

#### 6.5.1 `why`

Free-text retrieval over recorded intent.

**[ENV-013]** The `why` envelope **MUST** carry: `query` (the question as asked), `count` (number of
results returned), `cutoff` (the strong-match score threshold in effect), `score_stats`, and
`results`.

**[ENV-014]** `score_stats` **MUST** be an object with `top`, `runner_up`, and `median` — computed
over the **whole scored field**, not only the returned rows. This is what makes "a lone hit standing
above a flat tail" machine-detectable by the consumer rather than a judgement only the implementation
can make.

**[ENV-015]** Each entry in `results` **MUST** carry: `score`, `id`, `label`, `intent_kind`,
`claim`, `rationale`, `alternatives`, `source_file`, `source_location`, `provenance`,
`matched_terms`, `distinctive_matches`, `matched_coverage`.

**[ENV-016]** `alternatives` **MUST** be a list of strings. An implementation reading a legacy scalar
**MUST** coerce it to a single-element list, and **MUST NOT** iterate a bare string character by
character.

**[ENV-017]** The three evidence fields have fixed meanings, and an implementation **MUST NOT**
redefine them:

- `matched_terms` — which of the question's terms matched this result at all.
- `distinctive_matches` — the subset of `matched_terms` whose matched corpus token is
  **corpus-distinctive** rather than shared by nearly every record. A term every record contains
  carries no topical evidence.
- `matched_coverage` — a number in `[0, 1]`: the fraction of the question's **content** terms that
  matched.

**[ENV-018]** `matched_coverage` **MUST** be in `[0, 1]` inclusive.

**[ENV-019]** The `topically_weak` status **MUST** mean: the top result cleared the score cutoff,
but its match evidence does not support treating it as an answer. It is an **abstention above the
cutoff**, and it exists because a score-shaped answer and a real answer are otherwise
indistinguishable to a consumer that injects retrieved text into a working context without
skimming it. A consumer **MUST NOT** treat `topically_weak` as equivalent to `ok`.

**[ENV-020]** The `weak_match` status **MUST** mean: the top result scored *under* the cutoff but
stands clearly apart from the runner-up — a probable answer at moderate confidence, not noise.

> The exact thresholds and the scoring function are **out of scope** (§1.4). What is normative is
> that the four statuses are distinguishable and mean what [ENV-019]/[ENV-020] say.

#### 6.5.2 `list-intent`

**[ENV-021]** The `list-intent` envelope **MUST** carry `count`, `filter`, and `intent`. `filter`
**MUST** echo the filter that was applied, with an explicit `null` for each unset criterion — a
consumer must be able to see what was *not* filtered.

**[ENV-022]** Each entry in `intent` **MUST** carry: `id`, `label`, `intent_kind`, `claim`,
`rationale`, `source_file`, `source_location`, `confidence_score`, `provenance`.

#### 6.5.3 `explain`

**[ENV-023]** The `ok` variant **MUST** carry `query`, `resolved`, `intent`, `explains`, and
`relations`. `resolved` **MUST** report how the argument was matched (`matched_by`) and, for a
non-exact match, a `score`.

**[ENV-024]** The `ambiguous` variant **MUST** carry `candidates` and `message` and **MUST NOT**
carry `resolved`. Ambiguity is not a partial answer; an implementation **MUST NOT** silently pick a
candidate.

#### 6.5.4 `changed`

**[ENV-025]** The `changed` envelope **MUST** carry `base` (the reference diffed against, or null
when files were supplied explicitly), `changed_files`, `files_with_intent`, and `results`. Each
result **MUST** carry `file`, `matched_by`, `ambiguous`, and `governed_by`.

**[ENV-026]** `ambiguous` on a result **MUST** be true when the file was matched by basename and
that basename resolves to more than one path. A basename match that could mean several files
**MUST** be reported as such rather than silently resolved.

#### 6.5.5 `digest`

**[ENV-027]** The `digest` envelope **MUST** carry `since`, `added`, `removed`, and `superseded`.

#### 6.5.6 `coverage`

**[ENV-028]** The summary variant **MUST** carry a trusted-evidence block (`golden`) and a debt
block (`intent_debt`) alongside its coverage counts.

**[ENV-029]** A component of `intent_debt` that the implementation cannot compute **MUST** be
reported as explicit `null`, never as `0`. A zero claims "we measured and found none"; a null
honestly says "not measured". Reporting an unmeasured signal as zero is the same class of lie as
[REC-054]'s placeholder.

#### 6.5.7 `check`

**[ENV-030]** The `check` envelope **MUST** carry `rules` (count of rules evaluated),
`files_checked`, and `violations`.

**[ENV-031]** Each violation **MUST** carry the identifier of the decision it cites. A rule whose
failure cannot name the decision that motivated it is not a conformance check; it is a lint.

**[ENV-032]** A rule of a type the checker does not implement **MUST** be skipped — never counted as
a pass and never counted as a failure. Silence about an unimplementable rule is honest; a pass is
not.

#### 6.5.8 `intent-diff` and `review-context`

**[ENV-033]** Both **MUST** distinguish *governed by a decision* from *governed by a constraint*.
Deterministic inspection cannot tell conformance from violation, so an implementation **MUST NOT**
report a constraint touch as a proven violation.

#### 6.5.9 `capture`

**[ENV-034]** The `capture` envelope **MUST** carry `record` (the path as given, from which node
identity derives), `record_abs` (the resolved absolute destination), `node_id`, `title`,
`provenance`, `resolution_delta`, and `merged`.

**[ENV-035]** `record` and `record_abs` **MUST** both be reported. Reporting only the relative path
lets a success envelope hide a write into an unrelated working tree; reporting only the absolute one
hides the spelling that identity was derived from. They answer different questions and both are
needed.

**[ENV-036]** `merged` **MUST** report whether the derived view was updated, independently of
`status`. Writing the record and failing to update a derived index is an **honest partial success**:
the durable artifact exists, the derived view is stale. It **MUST NOT** be reported as a failure,
and **MUST NOT** be reported as an unqualified success.

**[ENV-037]** `resolution_delta` **MUST** be present with an explicit `null` when there was no
delta. This is a deliberate exception to [ENV-038] and exists because the consumer of this field is
asking a yes/no question that a missing key cannot answer.

### 6.6 Absent versus null

**[ENV-038]** A key **omitted** from an envelope or node **MUST** mean *not applicable to this
variant*. An explicit `null` **MUST** mean *applicable, and the value is known to be unavailable*.

**[ENV-039]** An implementation **MUST NOT** use the two interchangeably. Where the spec names a
present-with-null field ([ENV-029], [ENV-037], [ENV-041]), the key **MUST** be present.

### 6.7 Transport credential blocks

**[ENV-040]** `graph_identity` — or any equivalent block identifying *which corpus answered* —
**MUST NOT** be treated as a core envelope field. It is a **transport-layer credential block**.

The distinction is factual, not aesthetic. The command-line surface of the reference implementation
emits no such key on any envelope; the tool-call transport attaches it to every response,
unconditionally, after the result has been produced. Both surfaces compute it through the *same*
function — there is no divergent computation, only a difference in what is attached where. Modelling
it as a core field would make every command's schema depend on which transport carried it.

**[ENV-041]** A transport that attaches a credential block **MUST** attach it unconditionally, with
an explicit `null` when nothing resolved. A key that is sometimes absent is unusable as a
fail-closed signal, because the consumer cannot distinguish "nothing resolved" from "this transport
does not attach it".

**[ENV-042]** A transport-attached key **MUST NOT** collide with any key this specification assigns
to a command variant.

**[ENV-043]** Transport attachments are **NOT** governed by this specification's version marker
(§7). Adding, removing, or changing a credential block is a transport event, not a format event,
and **MUST NOT** trigger a spec version bump. Conversely, a consumer **MUST NOT** rely on the
presence of a transport attachment as evidence of any spec version.

---

## 7. Versioning policy

### 7.1 The rule

**[VER-001]** A **version marker and a migration note are REQUIRED exactly when a change alters how
an EXISTING field or section is interpreted** — a *meaning change*.

**[VER-002]** A change that **adds a new optional field or section** — a *vocabulary extension* —
**MUST NOT** require a version marker. Records written before the extension parse identically after
it; they simply lack the new optional data.

That is the whole rule. It is stated as a bright line because the alternative — bumping a version
for every addition — trains consumers to ignore version changes, which makes the marker worthless
on the day a real meaning change ships.

### 7.2 What crosses the line

**[VER-003]** Each of the following is a **meaning change** and **MUST** carry a version marker and
a migration note:

- Making an existing optional field **required**.
- Changing what the **absence** of an existing field means.
- Narrowing or re-interpreting an existing field's value space — including adding a value to a
  closed enumeration such as the provenance tiers ([PROV-001]).
- Changing how an existing section's body is parsed.
- Changing the ordering in [PROV-002].
- Changing an existing envelope key's type, or its meaning ([ENV-017] in particular).

**[VER-004]** Each of the following is a **vocabulary extension** and **MUST NOT** carry a version
marker:

- Adding a new optional section that older records simply lack.
- Adding a new optional field to an existing section, stripped from surrounding text so older
  records read identically.
- Adding a new key to a command variant that older consumers can ignore.
- Adding a new **command** to the union (§6.2) — an unknown tag is already required to be handled
  ([ENV-008]).

### 7.3 Absence stays honest

**[VER-005]** A change **MUST NOT** re-interpret the absence of a field in existing records as a
claim. Absence means *this was not recorded* and **MUST** continue to mean that after the change.

**[VER-006]** An implementation **MUST NOT** retroactively infer a value for a field that a record
does not carry. A wrong inference dressed as data is worse than an honest gap: the gap is visible
and the inference is not.

### 7.4 Scope of the version marker

**[VER-007]** The version marker governs **the record format and the core envelope only**. It does
**not** govern transport attachments ([ENV-043]), storage layouts, index formats, ranking
behaviour, or any other non-goal from §1.4.

**[VER-008]** The record format carries **no explicit version marker today**. A record is recognized
by its H1 shape alone ([REC-008]). This is a deliberate consequence of [VER-002]: every change to
date has been additive, so no marker has ever been required. [VER-001] is the rule that governs when
the first one becomes necessary — the marker's *format* is deliberately left unspecified until a
meaning change actually requires one, so that it can be designed against a real case rather than a
hypothetical.

---

## 8. Known gaps

Places where the reference implementation is genuinely silent or ambiguous. These are recorded as
gaps rather than filled with invented rules, because an invented rule is worse than an acknowledged
gap: implementers build on it, and it becomes real without ever having been decided.

| Id | Gap |
|---|---|
| **G1** | **Fenced code blocks are not excluded from parsing.** Headings and the inline status line are matched over raw text (§3.1). A record demonstrating record syntax inside a fence can change its own parse — and a `**Status:** Rejected` line in a fence causes the record to be excluded from ingest entirely ([REC-032]). Whether the fix is fence-aware scanning or scoping the status search to the pre-first-H2 region is undecided. |
| **G2** | **Section heading level is unconstrained.** `### Decision` and `###### Decision` are both accepted (§4.5). Whether parsers should tighten to level 2 or emitters should merely be constrained is undecided. |
| **G3** | **The `Context` section is written but never parsed.** The question is durable in the file, used for filename derivation ([REC-056]) and for legacy-record claiming ([REC-064]), yet never reaches the intent node (§4.5, [REC-021]). Whether the question should become a node field is undecided. |
| **G4** | **`resolution_delta` is not queryable.** Set on the node and reported at capture, but projected into no query result envelope ([REC-045]). The highest-signal field in the format is write-only from a consumer's point of view. |
| **G5** | **Assumption provenance does not inherit.** Every assumption is minted `authored` regardless of its record's kind ([PROV-007]). |
| **G6** | **`command` is not universal on every transport.** Four failure paths on the tool-call transport omit it ([ENV-012]). |
| **G7** | **Result field sets are not uniform across variants.** `list-intent` entries carry `confidence_score`; `why` result entries do not, though both describe the same nodes. Neither carries `resolution_delta`. There is no stated principle governing which node fields a given variant projects. |
| **G8** | **Multiple `## Decision` sections are first-wins with no diagnostic** ([REC-019]). A record with two Decision sections silently loses the second. Whether that should be an error is undecided. |
| **G9** | **No rule governs a record whose title is duplicated** within the same directory. Identity ([REC-071]) includes the source path, so two records with the same title in different files are distinct nodes; two records with the same title in the *same* file are not addressable separately. |
| **G10** | **The `attested` tier has no record syntax.** It is normatively ordered ([PROV-002]) but is produced from sources outside this format's scope (§1.4). A conforming implementation that only reads records will never mint it. |
| **G11** | **No version marker format exists** ([VER-008]). The rule for when one is required is decided; its syntax is not. |
| **G12** | **Empty `## Recommendation`.** [REC-046] says an empty recommendation yields no delta, but an emitter is not forbidden from writing an empty section, and a parser cannot distinguish "recommended nothing" from "recommendation section written and left blank". |

---

## 9. Conformance

A conforming implementation satisfies every **MUST** and **MUST NOT** in §§3–7 **that constrains an
implementation**, for the surfaces it implements. An implementation that only reads records need not
implement §6; an implementation that only answers queries need not implement §4.10 or §4.11.

Three classes of rule are **normative but outside conformance scope**, because no implementation can
be measured against them. They are marked in the rule index and are excluded from the corpus's
coverage obligation:

- **Governance rules** constrain how *this specification* may change — §7's versioning rules are the
  whole of this class. They bind the spec's editor, not an implementation, and there is no artifact
  an implementer could get wrong.
- **Consumer guidance** constrains how a *reader* of an envelope should behave — for example,
  treating an unrecognized status as a failure. The violation lives in a consumer's logic, not in any
  document a corpus can hold.
- **Action prohibitions** forbid an operation rather than constrain an output — for example, the
  prohibition on renaming an existing record. An implementation can produce every correct value and
  still perform the forbidden act afterwards, so no fixture can detect compliance.

The distinction matters because conflating these with implementation rules makes the corpus's own
coverage target unsatisfiable by construction, which in turn makes a coverage table that *looks*
complete only by quietly excusing the rules it cannot reach. Naming the class is honest; silently
omitting the rule is not. An action prohibition in particular stays a **MUST NOT** — being
unfixturable is not grounds for weakening it, and the rule against renaming exists to prevent an
identity-forking defect that no amount of output checking would catch.

Conformance is demonstrated against the **Whyfile conformance corpus** — a set of fixture records
and expected parse results, each keyed to the rule ids in this document. The corpus is the
executable form of this specification: where the prose and a fixture disagree, that disagreement is
a defect in one of them and **MUST** be resolved rather than papered over.

This document does **not** restate the corpus, and does not define conformance levels or profiles.
There is one format.

### 9.1 Rule index

Every normative rule, with its one-line statement.

#### Record format

| Id | Statement |
|---|---|
| REC-001 | The bare root filename `Whyfile` is RESERVED and explicitly unclaimed; implementations MUST NOT assign it a meaning. |
| REC-002 | A record MUST be a UTF-8 markdown document. |
| REC-003 | A parser MUST tolerate a leading BOM without changing the parse. |
| REC-004 | Headings match `^(#{1,6})\s+(.+)$`; a section body runs to the next heading of any level. |
| REC-005 | Section heading text MUST be matched case-insensitively. |
| REC-006 | YAML front matter MUST NOT be interpreted. |
| REC-007 | Unrecognized sections MUST be ignored without error. |
| REC-008 | A document is a record iff it has a matching H1 and a `Decision` section. |
| REC-009 | Record kind comes from the H1 form: ADR heading → `adr`, Decision heading → `decision`. |
| REC-010 | The first *matching* H1 wins; a non-matching H1 MUST NOT disqualify the document. |
| REC-011 | ADR heading grammar: `ADR-<digits>` + separator (em dash / en dash / colon / hyphen) + title, case-insensitive. |
| REC-012 | The ADR separator is REQUIRED; `# ADR-0007 Title` is not an ADR heading. |
| REC-013 | Heading recognition MUST NOT require a zero-padded or fixed-width digit run. |
| REC-014 | Decision heading grammar: `Decision:` + title, case-insensitive. |
| REC-015 | The title is the heading with its prefix removed and trimmed. |
| REC-016 | The title MUST be non-empty. |
| REC-017 | For a decision record the title is the chosen option. |
| REC-018 | Recognized sections: `Decision` (required), `Context`, `Alternatives considered`/`Alternatives`, `Recommendation`, `Assumptions`, `Status`. |
| REC-019 | When a heading appears more than once the first occurrence wins. |
| REC-020 | Records SHOULD write recognized sections at level 2 (parsers accept any level). |
| REC-021 | `Context` carries the question; emitters MUST render it, parsers MAY ignore it. |
| REC-022 | The alternatives body MUST be parsed as a flat list on `\d+.` / `-` / `*` markers. |
| REC-023 | Alternative text MUST be whitespace-collapsed, trimmed, and stripped of `**`; empty items dropped. |
| REC-024 | Alternatives MUST be yielded in document order. |
| REC-025 | A prose alternatives section MUST yield an empty list, not an error. |
| REC-026 | Records SHOULD NOT nest list items under an alternative; nesting is flattened. |
| REC-027 | Status MAY be given inline (`**Status:** X`) or as a `Status` section. |
| REC-028 | When both status forms are present, the inline form MUST win. |
| REC-029 | The inline status search spans the whole document; the first line-anchored match wins. |
| REC-030 | A status value MUST normalize to its first run of lowercase alphabetic characters. |
| REC-031 | An undeterminable status MUST be absent — no default, no explicit null. |
| REC-032 | A record whose status is `rejected` MUST NOT become ground truth, nor may its assumptions. |
| REC-033 | No status value other than `rejected` is normative. |
| REC-034 | Each assumption list item yields a `claim` plus two optional fields. |
| REC-035 | `(review by YYYY-MM-DD)` / `(review-by: …)` MUST be captured as `review_by` and stripped from the claim. |
| REC-036 | `review_by` MUST be a full ISO-8601 calendar date. |
| REC-037 | `(expires: …)` MUST be captured as free-text `expiry` and stripped from the claim. |
| REC-038 | Claim text MUST be whitespace-collapsed and trimmed of spaces and periods. |
| REC-039 | `review_by` / `expiry` MUST be omitted when absent, not null. |
| REC-040 | Supersession is collected from `supersedes ADR-N` over the whole document. |
| REC-041 | The passive form "superseded by ADR-N" MUST NOT be read as a supersession claim. |
| REC-042 | Supersession refs MUST be uppercased, de-duplicated, first-seen order. |
| REC-043 | A supersession target resolves by the first four-digit run in the target's filename. |
| REC-044 | An unresolvable supersession reference MUST be dropped silently. |
| REC-045 | A `Recommendation` differing from the title MUST yield `resolution_delta {recommended, chosen}`. |
| REC-046 | An absent, empty, or title-equal recommendation MUST yield no `resolution_delta` key. |
| REC-047 | `**Status:**` and `**Date:**` MUST be emitted on adjacent lines after the H1. |
| REC-048 | Emitted section order MUST be Context, Decision, Alternatives considered, Recommendation. |
| REC-049 | `Recommendation` MUST be emitted only when a non-empty recommendation was supplied. |
| REC-050 | Empty Context and empty Alternatives MUST render the literal `(none recorded)`. |
| REC-051 | An empty rationale MUST render the chosen option as the Decision body. |
| REC-052 | Alternatives MUST be emitted as a flat one-based `N. ` numbered list in supplied order. |
| REC-053 | An emitted record MUST end with a single trailing newline. |
| REC-054 | `(none recorded)` MUST be used only where absence is itself an answer, never where it means "nobody was asked". |
| REC-055 | A future optional section MUST be omitted entirely when empty, unless REC-054's first condition applies. |
| REC-056 | Filenames SHOULD be `YYYY-MM-DD-<question-slug>.md`, slugged from the question, not the chosen option. |
| REC-057 | Directory location is conventional, never normative; kind MUST NOT be inferred from it. |
| REC-058 | Slug derivation: lowercase, non-`[a-z0-9]` runs → single `-`, strip edges. |
| REC-059 | A slug MUST be bounded at 60 characters. |
| REC-060 | Truncation MUST land on a word boundary. |
| REC-061 | A first word exceeding the bound MUST be hard-cut — the only permitted mid-word cut. |
| REC-062 | An empty slug MUST become the literal `decision`. |
| REC-063 | A slug MUST NOT be able to contain a glob metacharacter. |
| REC-064 | A legacy `<slug-of-chosen>.md` MUST be reused when its `## Context` equals the question. |
| REC-065 | A legacy file MUST NOT be claimed on filename alone, nor when unreadable or unrecognized. |
| REC-066 | An empty question matches only a recorded context of `(none recorded)`. |
| REC-067 | Otherwise reuse the lexicographically first existing dated record for the same question slug, whatever its date. |
| REC-068 | The dated-record glob MUST use digit character classes; `*` and `?` forms are forbidden. |
| REC-069 | Otherwise the destination MUST be `<today>-<question-slug>.md`. |
| REC-070 | An implementation MUST NOT rename an existing record; identity derives from the path. |
| REC-071 | Node identity MUST hash `path :: location :: kind :: normalized-label`. |
| REC-072 | Normalized label: lowercase, non-`[a-z0-9]` runs → `_`, strip edge `_`. |
| REC-073 | The source path in identity MUST be repository-relative, POSIX-separated. |
| REC-074 | A path outside a repository falls back to POSIX absolute; canonicalization MUST NOT raise. |

#### Provenance

| Id | Statement |
|---|---|
| PROV-001 | Provenance MUST be one of exactly four values; the set is closed. |
| PROV-002 | The total order MUST be `authored > captured > attested > reconstructed`. |
| PROV-003 | Absent or unrecognized provenance MUST rank as `reconstructed`. |
| PROV-004 | Trust ordering MUST use provenance as primary key, numeric confidence as secondary. |
| PROV-005 | An ADR record MUST yield `authored` intent. |
| PROV-006 | A decision record MUST yield `captured` intent. |
| PROV-007 | An assumption SHOULD inherit its record's provenance tier. |
| PROV-008 | Intent ingested from a record MUST carry confidence `1.0`. |
| PROV-009 | Provenance MUST NOT be conflated with a numeric or string confidence label. |
| PROV-010 | The golden (trusted) tiers MUST be exactly `{authored, captured, attested}`. |
| PROV-011 | `reconstructed` intent MUST NOT count toward any trusted-evidence metric. |
| PROV-012 | A blended trust metric MUST also report the per-tier breakdown. |

#### Envelope

| Id | Statement |
|---|---|
| ENV-001 | A result MUST be a single JSON object. |
| ENV-002 | Every envelope MUST carry `command`. |
| ENV-003 | Every envelope MUST carry `status`, a lowercase snake_case token. |
| ENV-004 | `command` and `status` are the ONLY universal keys. |
| ENV-005 | The envelope MUST be a tagged union discriminated by `command`, not one struct of optionals. |
| ENV-006 | Where one `command` carries disjoint shapes, the secondary discriminator MUST be named and applied first. |
| ENV-007 | Status tokens are per-command, not global. |
| ENV-008 | An unrecognized status MUST be treated as a failure. |
| ENV-009 | A status MUST NOT be overloaded to carry data. |
| ENV-010 | An honest-negative status is a complete answer, not an error. |
| ENV-011 | The error variant MUST carry `command`, `status`, and `message`. |
| ENV-012 | A consumer MUST NOT assume a variant key is present merely because `command` names that variant. |
| ENV-013 | `why` MUST carry `query`, `count`, `cutoff`, `score_stats`, `results`. |
| ENV-014 | `score_stats` MUST carry `top`, `runner_up`, `median` over the whole scored field. |
| ENV-015 | Each `why` result MUST carry the 13 named fields including the three evidence fields. |
| ENV-016 | `alternatives` MUST be a list of strings; a legacy scalar MUST be coerced, never iterated. |
| ENV-017 | `matched_terms`, `distinctive_matches`, `matched_coverage` have fixed meanings. |
| ENV-018 | `matched_coverage` MUST be in `[0, 1]`. |
| ENV-019 | `topically_weak` MUST mean abstention above the cutoff and MUST NOT be read as `ok`. |
| ENV-020 | `weak_match` MUST mean a probable answer below the cutoff with a clear margin. |
| ENV-021 | `list-intent` MUST carry `count`, `filter`, `intent`; `filter` echoes unset criteria as null. |
| ENV-022 | Each `list-intent` entry MUST carry the nine named fields. |
| ENV-023 | `explain` `ok` MUST carry `query`, `resolved`, `intent`, `explains`, `relations`. |
| ENV-024 | `explain` `ambiguous` MUST carry `candidates` and `message` and MUST NOT auto-select. |
| ENV-025 | `changed` MUST carry `base`, `changed_files`, `files_with_intent`, `results`. |
| ENV-026 | A basename match resolving to several paths MUST be reported `ambiguous`. |
| ENV-027 | `digest` MUST carry `since`, `added`, `removed`, `superseded`. |
| ENV-028 | `coverage` (summary) MUST carry a trusted-evidence block and a debt block. |
| ENV-029 | An uncomputable debt component MUST be explicit `null`, never `0`. |
| ENV-030 | `check` MUST carry `rules`, `files_checked`, `violations`. |
| ENV-031 | Each violation MUST cite the decision it enforces. |
| ENV-032 | An unimplemented rule type MUST be skipped — never a pass, never a failure. |
| ENV-033 | Constraint-governed change MUST NOT be reported as a proven violation. |
| ENV-034 | `capture` MUST carry `record`, `record_abs`, `node_id`, `title`, `provenance`, `resolution_delta`, `merged`. |
| ENV-035 | Both the as-given and resolved record paths MUST be reported. |
| ENV-036 | `merged` MUST report derived-view update independently of `status`. |
| ENV-037 | `resolution_delta` MUST be present with explicit `null` when there is no delta. |
| ENV-038 | Omitted means "not applicable"; explicit null means "applicable, value unavailable". |
| ENV-039 | The two MUST NOT be used interchangeably. |
| ENV-040 | A corpus-identity block MUST NOT be a core envelope field; it is a transport credential block. |
| ENV-041 | A transport attaching a credential block MUST attach it unconditionally, null when unresolved. |
| ENV-042 | A transport-attached key MUST NOT collide with any spec-assigned variant key. |
| ENV-043 | Transport attachments are NOT governed by the spec's version marker. |

#### Versioning

| Id | Statement |
|---|---|
| VER-001 | A version marker and migration note are REQUIRED exactly when a change alters how an existing field or section is interpreted. |
| VER-002 | Adding a new optional field or section MUST NOT require a version marker. |
| VER-003 | Six named changes are meaning changes and MUST carry a marker (including adding a provenance tier). |
| VER-004 | Four named changes are vocabulary extensions and MUST NOT carry a marker (including adding a command). |
| VER-005 | A change MUST NOT re-interpret the absence of a field in existing records as a claim. |
| VER-006 | An implementation MUST NOT retroactively infer a value for an unrecorded field. |
| VER-007 | The version marker governs the record format and core envelope only. |
| VER-008 | The record format carries no explicit version marker today; the marker's format is intentionally unspecified until a meaning change requires one. |

---

## 10. Divergences flagged for the reference implementation

Recorded here so they are visible to a reader of the spec, and routable by its maintainers. This
document specifies what **should** be; it does not modify any implementation.

| Rule | Divergence |
|---|---|
| **[PROV-007]** | Assumption nodes are minted `authored` unconditionally, so a `captured` record's assumptions outrank the decision that stated them and are counted as reviewed ground truth. Trust inversion. |
| **[ENV-002] / [ENV-012]** | Four failure paths on the tool-call transport emit envelopes with no `command` key, while the same failures on the command-line surface carry it. The one key called universal is not universal on every transport. |
| **[ENV-006]** | `coverage` overloads a single `command` tag with two disjoint payloads, forcing a secondary structural discriminator. A distinct tag would flatten the union. Changing it is a meaning change under [VER-001]. |
| **[REC-005] / G1** | Headings and the inline status line are matched over raw text with no fenced-code-block exclusion. A fenced `**Status:** Rejected` silently excludes a record from ingest. |
| **G7** | Result field sets differ across variants describing the same nodes (`confidence_score` on `list-intent` but not `why`; `resolution_delta` on neither), with no stated projection principle. |
