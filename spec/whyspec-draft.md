# The Whyspec Specification

**Version:** 0.2 — working draft. The record-format version and its marker are defined in §7.6;
the migration table there records what changed since 0.1.
**Status:** Draft. Not frozen. Not a standard. Rule ids are stable within this draft and are
referenced by the conformance corpus; rule *text* may still change.

---

## 1. Preface

### 1.1 What this document is

This is the normative description of the **why record format**: a plain-markdown record of a
decision — what was chosen, what else was on the table, and why — that lives in the repository
whose code the decision governs.

The format exists because the reasoning behind code is the part that does not survive. Diffs
survive, tests survive, the argument that produced them does not. A why record makes that
argument a file: greppable, reviewable, diffable, and mechanically ingestible into a queryable
decision layer.

This document specifies three things and only three:

1. **The record format** — how a why record is written and how a conforming parser reads it.
2. **The recall envelope** — the shape of the text that delivers governing decisions to a writer
   at a coupling point.
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
| `ENV-nnn` | Envelope — the recall envelope (§6) and the reserved command variants (Appendix A) |
| `VER-nnn` | Versioning policy — when a change requires a version marker |
| `INT-nnn` | Intent-layer profile (`profiles/intent-layer.md`) — intention, attestation, recall line |

A complete index of every rule id appears in §9.

### 1.3 Scope

In scope:

- The on-disk syntax of a decision record, and the deterministic rules for parsing one.
- Which fields a parsed record yields, and which are optional.
- Filename derivation, and the compatibility rules that keep an existing record's identity stable.
- The provenance tiers and their total order.
- The recall envelope a writer receives.
- The rule that governs when a format change requires a version marker.

### 1.4 Non-goals

The following are deliberately **not** specified here. A format specification that pins an
implementation stops being implementable by anyone else, and each item below is a place where
implementations should be free to differ.

- **Storage.** Whether records are read from a working tree, a git object database, an index, a
  cache, or a network service. The format says what a record *is*, not where it lives.
- **Transport.** How a query reaches an implementation or how an answer is returned — process
  invocation, HTTP, a tool-call protocol, a library call. §6.2 and Appendix A.6 draw the line between the
  spec-governed envelope and whatever a transport wraps around it.
- **Ranking and retrieval.** How an implementation scores a free-text question against a corpus of
  records. The reserved `why` variant names fields for scores and match evidence (Appendix A.5.1) and constrains their
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

**why record** — a decision record in this format. Lowercase and generic, like "an OpenAPI
document" — not a proper noun. Conventionally stored under `docs/decisions/`.

**`why`** — the command and package name, always lowercase and set in monospace.

**Whyspec** — the name of this specification.

**Attrica** — the hosted product built on this specification. *Why this, not that.*

**Record** — a why record. Used interchangeably.

**Record kind** — one of the two forms a record may take: an **ADR record** or a **decision
record** (§4.1).

**Intent node** — the structured object a parsed record becomes when ingested into a queryable
decision layer. The format specifies the parse; the node is what a query answers with.

**Provenance tier** — the trust class of a piece of intent (§5).

**Envelope** — the recall envelope (§6), the text that delivers governing decisions to a writer; the
reserved command envelopes are described in Appendix A.

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
to `why.config.toml`, and the bare capitalized name it briefly held was retired.

"Whyfile" was then re-purposed to name the decision record itself, capitalized in the style of
`Makefile` or `Dockerfile`, and this specification carried that name and that convention through
its early drafts. The term has since been retired a second time: this document and its project
are now named **Whyspec**, and an individual record is a **why record** — lowercase, generic, not
a proper noun. "Whyfile" survives only as the literal reserved root filename in [REC-001] above,
and in archived documents using one of the two earlier senses. A reader encountering it elsewhere
is looking at a different thing that happened to share a name.

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

> Headings, the status line and the inline fields are recognised over the document with its fenced
> code blocks masked — [REC-158] in §3.2. A `## Decision` heading or a `**Status:** Rejected` line
> inside a fence is quoted text, not structure.

### 3.2 What is not read

**[REC-006]** YAML front matter, if present, **MAY** be interpreted, but **only** as a
lower-precedence source that can never override the markdown body, and **only** for the keys named
in [REC-149]. Every other key **MUST NOT** be interpreted.

> A record's meaning is determined by its body for anything the body can express, and that fails
> only for a title the body never states: some projects keep records with no level-1 heading at all,
> the title living solely in front matter. The precedence direction is what makes reading it safe.
> Front matter never wins, so no record's meaning can be changed by a value a static-site generator
> wrote.

**[REC-149]** The only front-matter key a parser **MAY** interpret is `title`, and it **MUST** be
used only where the document has no level-1 heading at all. Where an H1 exists, the H1 title
**MUST** win.

**[REC-150]** `status` **MUST NOT** be read from front matter, even where the body states no status.
A status determines whether a record is ingested at all, so a `status:` key written by external
tooling for its own purposes could silently remove records from a corpus. This asymmetry with
[REC-149] is deliberate: a wrong title is visible and harmless, a wrong status is invisible and
deletes.

**[REC-132]** Where a document's first line is exactly `---`, the bytes from that line through the
next line that is exactly `---`, inclusive, are **YAML front matter** and **MUST** be removed before
any other rule in §3 or §4 is applied. A heading, status line, or section appearing inside front
matter is therefore not structural. Where no closing `---` exists, the document has **no** front
matter and is scanned whole.

> [REC-006] says front matter is not *interpreted* and does not say whether it is *removed*, and §3
> defines a body only for a section ([REC-004]), never for a document — so the two readings are
> observably different and neither is decided. A `# Decision: X` line inside front matter is a
> level-1 heading under the leave-it-alone reading and nothing at all under the removal reading; a
> `**Status:** Rejected` line inside front matter excludes the record from ingest under one reading
> and not the other, because [REC-029] deliberately searches the whole document.
>
> Removal is the smaller rule because it needs no exception anywhere else: [REC-029]'s
> whole-document search, [REC-040]'s whole-document supersession scan and [REC-010]'s
> first-matching-H1 rule all stay exactly as written. [REC-003]'s leading-BOM tolerance composes —
> the BOM is stripped first, so a BOM followed by `---` opens front matter.

**[REC-158]** A **fenced code block** — the lines from one whose trimmed text begins with three
backticks or three tildes, through the next line whose trimmed text begins with the **same**
marker, inclusive — is quoted text. No heading ([REC-004]), status line ([REC-027], [REC-147]),
identifier line ([REC-139]) or date field **MUST** be read from a line inside one. A fence closes
only with its own marker: a `~~~` line inside a backtick fence is content, not a closer. A fence
that is never closed runs to the end of the document. Fenced lines inside a section remain part of
that section's body under [REC-004]; only structural recognition ignores them.

> This closes what §8 recorded as gap G1, on evidence rather than by invention. The hazard was
> never hypothetical: a record that quoted its predecessor's header inside a fence acquired the
> quoted identifier line, and the duplicate identifier silently un-retired a record that had
> genuinely been superseded. A fenced `**Status:** Rejected` does the inverse — it retires a live
> record — and [REC-029]'s whole-document search makes it certain to be found.
>
> Masking rather than parsing is the smaller rule and fails in the safe direction. A reader that
> tracks one open marker per document is not a Markdown parser, and what it misreads it *skips*:
> the failure mode is a heading not seen, never a heading fabricated. Closing only on the same
> marker is what CommonMark specifies and what keeps a tilde fence containing a backtick example
> from ending early. Bodies keep their fences because a decision that shows the command it
> decided on has lost nothing by showing it.

**[REC-007]** A parser **MUST NOT** require any section not named in §4. Unrecognized sections
**MUST** be ignored without error. This is what makes §7's vocabulary-extension rule safe.

---

## 4. Record format

### 4.1 The two record kinds

**[REC-008]** A markdown document is a record **if and only if** both of the following hold:

1. It contains a `Decision` section (§4.5), **and**
2. either a level-1 heading matching one of the three declared forms (§4.2, §4.3, §4.3.1), **or**
   a level-1 heading of any shape together with the **ADR section signature** (§4.3.2).

A document failing either condition **MUST NOT** be treated as a record. This is what allows a
template, a README, or an unrelated document to sit in the same directory without being ingested.

> **Why a bare heading is not sufficient on its own.** Meeting notes routinely carry a `Decision`
> section — `# Weekly sync notes` followed by `## Decision` and `## Alternatives considered` is a
> real shape, and it is not a decision record. The heading form is what separates the two, so it is
> relaxed rather than removed.

**[REC-009]** The record kind is determined by which level-1 form matched:

| H1 form | Kind | Provenance tier |
|---|---|---|
| `# ADR-<digits><sep> <title>` | `adr` | `authored` (§5) |
| `# <digits>. <title>` | `adr` | `authored` (§5) |
| `# Decision: <title>` | `decision` | `captured` (§5) |
| bare `# <title>` with the ADR section signature | `adr` | `authored` (§5) |

`Decision:` is the form a capture tool emits at the moment of choosing, which is why it alone implies
`captured`. Every other recognised form is a document a person wrote, and takes `authored`.

**[REC-010]** A parser **MUST** use the **first** level-1 heading that matches any declared form as
the record's title heading, and **MUST** ignore any later level-1 heading. A level-1 heading that
matches neither form **MUST NOT** disqualify the document: the parser continues looking.

> A document whose first H1 is `# Notes` and whose second is `# Decision: A` parses as a decision
> record titled `A`.

### 4.1.1 Numbered heading grammar

**[REC-142]** A numbered heading **MUST** match `<one or more digits>. <title>` — digits, a full
stop, whitespace, then a non-empty title. It denotes an `adr` record with `authored` provenance.

> This is the numbering emitted by `adr-tools`, the reference implementation of Michael Nygard's
> Architecture Decision Record convention, and by every tool derived from it. Measured across the
> corpora of the three principal ADR tools, 34 of 84 real records used this form and **none** used
> `ADR-N:` or `Decision:`. A grammar that recognises no record any established tool produces is
> not interoperable, whatever its internal consistency.

### 4.1.2 The ADR section signature

**[REC-143]** A level-1 heading of any other shape **MUST** be accepted as a record heading **if
and only if** the document carries an **ADR section signature**, which is either:

- both `## Context` and `## Consequences` (the Nygard shape), **or**
- `## Context and Problem Statement` (the MADR shape).

The MADR heading stands alone because the `Decision` gate of [REC-008] has already been satisfied,
and no document but an ADR pairs that heading with a decision.

`## Status` is **not** part of the signature, and requiring it would be a defect rather than a
tightening: a real ADR corpus omits `Status` entirely, keeping it in front matter or nowhere.
`Context` with `Consequences`, on top of the `Decision` gate, is already a shape notes do not
have — the meeting-notes counter-example for [REC-001] carries neither.

**[REC-144]** The signature **MUST NOT** be weakened to a subset. A document carrying only
`## Decision` alongside an arbitrary heading **MUST NOT** be treated as a record: that shape is
indistinguishable from meeting notes, and admitting it converts every set of minutes containing a
decision into a governing record.

> 48 of the 84 measured records used a bare title. The signature is what makes them recognisable
> without also admitting notes. Verified: relaxing the heading rule this way recovered 32 real
> records from the tool corpora while adding **zero** false positives across 3,390 markdown files
> in nineteen real repositories.

### 4.1.3 Section aliases

**[REC-145]** A parser **MUST** accept the following alternative spellings as the sections named,
and **MUST** treat them as carrying the same obligation:

| Canonical section | Also spelled |
|---|---|
| `Context` | `Context and Problem Statement` |
| `Decision` | `Decision Outcome`, `Amendment` |
| `Alternatives` / `Alternatives considered` | `Considered Options` |
| `Governs` | `Governed paths`, `Governs files` |

The first three rows are the MADR spellings. Measured across the ADR directories of the three
principal ADR tools, 46 of 64 real records used the MADR template, and a format recognising only one
template's spelling of a section recognises neither in practice. `Amendment` is the operative section
of a constitutive record — one whose body amends a standing decision — and the first external index
found such a record, shaped Context / Amendment / Consequences, rejected for that one heading. The
`Governs` spellings were found the same way: a record listing real globs under `## Governed paths`
rendered as *scope not declared*.

**[REC-157]** A `Governs` alias **MUST** count as the record's declared scope only where its body
yields at least one item under [REC-082]. Where an alias body yields no item, the record's scope
**MUST** be read as *not declared* ([REC-084]), never as *governs nothing*. The canonical `## Governs`
heading is unaffected: an empty canonical section keeps its meaning under [REC-084]'s distinction.

> The asymmetry is deliberate. A writer who typed `## Governs` and left it empty made a statement
> about scope; a writer who typed `## Governed paths` and wrote a paragraph — "this decision governs
> future work in the daemon" — was writing prose under a heading this format did not name. Reading
> that prose as *governs nothing* would strip a repository-wide default from a record that plainly
> meant to claim scope, which is strictly worse than the default it gets today. Where the body
> yields items, the alias is the same obligation under a different heading, exactly as the other rows.

**[REC-146]** A section heading **MAY** carry a trailing HTML comment, and a parser **MUST** ignore
it when matching the heading. `## Decision Drivers <!-- optional -->` is emitted by the MADR
template itself, so a parser that matches headings exactly rejects the template's own output.

**[REC-147]** `Status` **MAY** additionally be written as a list item, `- Status: <value>`, and a
parser **MUST** read it where no inline `**Status:**` field is present. This is the form MADR uses;
a parser reading only the inline field and the `## Status` section reports no status for a record
that plainly states one.

**[REC-160]** A list item whose text begins with the inline field — `- **Status:** <value>` — is
the list-item form of [REC-147] wearing both markers, and a parser **MUST** read it as a list-item
status, with the list-item form's precedence. The list-item forms are recognised only with their
marker, `-` or `*`, at the start of the line; an indented list item is not a status field.

**[REC-161]** `Status` **MAY** also be written bare — a line that begins `Status:` after any
leading whitespace, case-insensitively, with no emphasis and no list marker — and a parser **MUST**
read it where neither an inline field nor a list-item form is present. The sources are consulted in this order
over the whole document, each only where every earlier one is absent: the inline field
([REC-027], [REC-029]), the list-item forms ([REC-147], [REC-160]), the bare line, and last the
`## Status` section ([REC-028]). Within each source the first line outside a fenced block wins.

> Three spellings of one field, because three communities write it three ways and each is
> unambiguous on its own. The precedence is by strength of signal rather than by position: an
> inline field anywhere in the document outranks a bullet or a bare line earlier in it, so a record
> that states its status the canonical way is never overruled by a looser one.

### 4.1.4 Unfilled templates

**[REC-148]** A record whose title is a **placeholder MUST NOT** be treated as a record. A title is
a placeholder when any of the following hold:

- every alphabetic word in it is an upper-case template token (`NUMBER`, `TITLE`, `DATE`, `STATUS`,
  `CONTEXT`, `DECISION`, `CONSEQUENCES`, `SHORT`, `PROBLEM`, `SOLUTION`, `TEMPLATE`, `OPTION`,
  `DRIVER`);
- it contains a **shape placeholder** — a word standing for a value's form rather than naming a
  field: `NNN`, `NNNN`, `NN`, `XXX`, `XXXX`, `YYYY`, `MM`, `DD`. One is decisive, because these do
  not occur in real titles;
- the whole title is enclosed in square brackets, or it contains a bracketed segment whose words are
  all template tokens — a template numbered in sequence with its siblings reads `ADR000: [TITLE]`.

> This is a **heuristic and will never be complete**: a template is structurally identical to the
> records it is a template for, so only its unfilled text distinguishes it. Four distinct
> placeholder conventions were observed across four repositories, and a fifth is likely. A parser
> **MUST NOT** treat template exclusion as a guarantee.

> [REC-008] states that a template must be able to sit in a record directory without being
> ingested. A template satisfies every structural test — it carries the full section signature,
> because a template *is* the set of headings — so structure alone cannot exclude it. Only the
> unfilled title can. Measured: in one real repository two of seven apparent records were the
> `adr-tools` and MADR templates.

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
| `Alternatives considered` *or* `Alternatives` | no | `alternatives` — an ordered list (item shape per [REC-134]) |
| `Recommendation` | no | `recommendation` — the section body, trimmed |
| `Assumptions` | no | `assumptions` — a list of structured claims (§4.7) |
| `Status` | no | fallback status source (§4.6) |

**[REC-019]** When more than one section matches the `Decision` heading, the parser **MUST** use the
**first** and ignore the rest. The same first-wins rule applies to every heading in the table.

**[REC-162]** Where the operative section selected under [REC-018], [REC-019] and [REC-145] —
`Decision`, or failing that one of its aliases — has an empty body ([REC-004]) and headings of level
3 or deeper follow it before the next level-2 heading, the parser **MUST** compose `rationale` from
those subsections in document order: each subsection's heading text, then its body, joined by blank
lines. Where that body is non-empty, [REC-004] applies unchanged and no subsection is joined.

> A constitutive record puts its whole decision under `### A1`, `### A2` … with nothing between
> the `## Amendment` heading and the first subsection. Under [REC-004] alone that record has an
> empty rationale, which [REC-140] must then yield as an empty string — a decision that says
> nothing, from a record that says everything. Composition is confined to the empty-body case so
> that [REC-004]'s rule for an ordinary record — the body stops at the next heading of any level —
> is untouched.

**[REC-163]** Where a record has an operative section, every level-2 section whose heading's first
word is `Why`, matched case-insensitively — `## Why`, `## Why not a cache`, `## Why the picker is
excluded` — **MUST** be joined to `rationale` after the operative body (as composed by [REC-162]
where that applies), in document order, each separated by a blank line. A heading whose first word
merely begins with `Why` (`## Whyspec setup`) is not such a section. Where two sections share a
heading, the first is used and the rest ignored, as [REC-019] rules for every heading.

> A record that answers "why" under a heading called *Why* has put its rationale exactly where a
> reader would look for it, and a parser that kept the Decision and dropped the Why would keep the
> what and lose the why.

**[REC-020]** Records **SHOULD** write all sections in [REC-018] at heading level 2.

> Parsers **MAY** accept section headings at any level; only the title heading is level-constrained.
> [REC-020] is a SHOULD on emitters and deliberately not a MUST on parsers, because tightening
> parsers to level 2 would reject records already in the field. See §8, Q2.

**[REC-021]** The `Context` section carries the **question** the record answers. Emitters **MUST**
render it (§4.10).

**[REC-107]** A parser **MUST** yield the `Context` body as a `question` field on the parsed
record, and it **MUST** reach the intent node. An empty or absent `Context` yields an absent
`question`, never an empty string.

> The question is what identifies a decision: it is why the filename derives from it (§4.11) and
> why re-deciding updates a record rather than forking one, so a representation that omitted it
> could not recognise two answers to the same question.
>
> The asymmetry was not merely a missing field. **The question is what identifies a decision.**
> A record is the answer currently occupying a question-shaped slot: that is why the filename is
> derived from the question rather than from the chosen option, and why re-deciding the same
> question updates an existing record instead of forking a new one. A representation that omits
> the question therefore omits the very thing that makes two records comparable, and cannot
> recognise that two answers written a year apart address the same slot.
>
> It is also the retrieval key. A reader's query is almost always shaped like the question, while
> a record without one can only be matched against its answer.

**[REC-140]** A `Decision` section whose body is empty **MUST** yield `rationale` as an **empty
string**, not an absent key.

> Stated the opposite way from `question` ([REC-107]) on purpose. The section's presence is what
> [REC-008] tests; its emptiness is a fact about the record, not an absence of one. A record with no
> Decision section is not a record at all, so an absent `rationale` key could never be observed, and
> giving it a second meaning would draw a distinction nobody can act on. [REC-051] governs the same
> case on the write path and is unaffected.

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
meaning in this format: a conforming parser flattens every marker to a top-level item, so
a sub-bullet becomes an alternative in its own right.

#### 4.5.2 Alternative disposition

**[REC-097]** An alternative item **MAY** carry a **disposition** and a **rejection rationale**,
in the form `<option> — <disposition>: <rationale>`.

**[REC-098]** `<disposition>` **MUST** be one of exactly `rejected`, `deferred`,
`partially-adopted`, or `not-evaluated`. The set is closed; adding one requires a version marker
(§7).

**[REC-099]** An alternative carrying no disposition **MUST** yield the whole item as its option
text, with disposition and rationale absent. This preserves [REC-022]–[REC-025] exactly: a bare
string remains a valid alternative.

**[REC-100]** `deferred` **MUST NOT** be treated as equivalent to `rejected`. A deferred option
remains available.

**[REC-133]** In [REC-097]'s form the separator is exactly one of em dash `—` (U+2014), en dash `–`
(U+2013), or hyphen-minus `-`, with at least one whitespace character on **each** side. The
disposition token **MUST** be matched case-insensitively and yielded lowercased. An item whose token
is not in [REC-098]'s closed set carries **no** disposition: [REC-099] applies unchanged and the
whole item, separator included, is the option text.

> The separator set is [REC-011]'s less the colon, which [REC-097] already spends on introducing the
> rationale — the same question answered in one place and not the other. Requiring whitespace on both
> sides is what keeps a hyphenated option name (`blue-green deploy`) from being read as a separator.
> The last sentence makes the unrecognized-token case additive rather than lossy, for the reason
> [REC-099] gives: absence of a disposition means *not recorded*, never that none existed.

**[REC-134]** The `alternatives` a parser yields are **objects**, each carrying `option` and, where
recorded, `disposition` and `rationale` ([REC-097]–[REC-099]). [REC-018]'s earlier "ordered list of
strings" is **superseded** by this rule. [ENV-016] continues to govern the **envelope** field
`alternatives`, which projects each alternative's `option` text only; an implementation **MUST NOT**
emit an object there.

> The parsed object carries the three parts [REC-097]–[REC-099] require, which a string cannot
> hold; keeping the projection at the envelope is what lets the envelope rule stand unchanged. The
> parse gains structure, the wire format does not.

This is the format's answer to its own central question. A decision that records only what was
chosen has recorded a commitment; a decision that records why the alternatives *lost* has
recorded a belief. Two teams that chose the same option for opposite reasons — one rejecting the
alternative on operating cost, one on data-model fit — hold different beliefs and will diverge at
the next decision, and a format that stores both cases identically cannot show why.

The distinction [REC-100] draws is the one most often lost. "We ruled this out" and "we might
still do this" are different states of the world, and a corpus that conflates them cannot answer
what it has left on the table.

The **record syntax** accepts every bare alternative unchanged ([REC-099]), with disposition simply
absent. Absence means *not recorded*, never *no disposition existed*. The **parse result** is the
object shape [REC-134] defines; the envelope remains the string projection [ENV-016] defines. Both
are baseline contracts, not migrations from an earlier published shape.

### 4.6 Status

**[REC-027]** A record's status **MAY** be given in either of two forms:

- **Inline** — a line matching `^\s*\*\*status:?\*\*\s*:?\s*(.+?)\s*$`, case-insensitively. This
  tolerates `**Status:** X`, `**Status**: X`, and `**Status** : X`.
- **Section** — a `## Status` section, whose body supplies the value.

**[REC-028]** When both forms are present the **inline** form **MUST** win.

**[REC-029]** The inline form **MUST** be searched over the whole document, and the **first**
line-anchored match **MUST** win. It is not scoped to any section.

**[REC-030]** A status value **MUST** be normalized by **lowercasing it and then taking its first
run of alphabetic characters**. `Rejected in favor of ADR-9`, `: Rejected.`, and `REJECTED` all
normalize to `rejected`. A value containing no alphabetic characters normalizes to absent.

> The order matters: lowercase first, then select. Selecting a lowercase run first would make
> `REJECTED` normalize to **absent**, and an absent status is *unstated* ([REC-101]), which takes its
> tier from the record kind and yields ground-truth intent — a record declined in capitals would be
> published as a trusted commitment, the inversion [REC-032] and [REC-104] exist to prevent.

**[REC-031]** When no status can be determined, the parsed record's status **MUST** be absent. An
implementation **MUST NOT** substitute a default, and **MUST NOT** serialize an explicit null in
place of the field on the resulting intent node — the key is omitted entirely. See [ENV-038] for
the general absent-versus-null convention.

**[REC-032]** A record whose normalized status is `rejected` **MUST NOT** become ground-truth intent
of any tier, and its assumptions **MUST NOT** either. A rejected record is the option *not* taken;
ingesting it would invert its meaning.

**[REC-033]** The status values carrying normative behaviour are exactly those classified in
§4.6.1 — `draft`, `proposed`, `accepted`, `rejected` — together with the unstated case
([REC-101]). Any **other** value is conventional, and an implementation **MUST NOT** attach
behaviour to it beyond [REC-032] and the unrecognized-status row of [REC-101].

> This does **not** admit `superseded` as a status: [REC-108] excludes it, and currency is derived
> from the relation graph. It is conventional text that parses and normalizes and contributes
> nothing.

#### 4.6.1 Settled and unsettled status

Status carries **two independent properties**, and collapsing them onto one axis is what makes
`rejected` look like an unfinished thought rather than the most settled state a record can reach.

**[REC-101]** A record's normalized status ([REC-030]) **MUST** determine every one of the
following, by lookup in this table and by no other means. **This table is the sole normative
source for the behaviour of a status**; where any other rule appears to assign one of these
columns, this table governs.

| Normalized status | Deliberation | Offered | Disposition | Yields | Counted in trust metrics | Currency defined |
|---|---|---|---|---|---|---|
| `draft` | open | **no** | — | provisional intent, marked open and unoffered | no | no |
| `proposed` | open | yes | — | provisional intent, marked open | no | no |
| `accepted` | resolved | yes | **adopted** | ground-truth intent | yes | **yes** |
| `rejected` | resolved | yes | **declined** | **foreclosure intent** | no | no |
| *absent* | **unstated** | — | **adopted** | ground-truth intent, tier from record kind | yes | **yes** |
| *any other value* | **unstated** | — | **adopted** | ground-truth intent, tier from record kind | yes | **yes** |

Every row, including the two `open` rows, **MUST** be ingested. The distinctions in the table
**MUST NOT** be collapsed: `draft` and `proposed` differ in whether they were offered, while an
absent and an unrecognized status are both `unstated`, are treated identically, and **MUST NOT**
be read as `open`. Open intent remains queryable but does not count toward trusted-evidence
metrics ([PROV-010]).

The two `unstated` rows follow the format's honest-absence discipline. `open` is a claim an author
made; absence is no claim, and an unrecognized token conveys no behaviour the format understands.
Reading either as open would invent a deliberation state the author never recorded.

**[REC-110]** A review surface **SHOULD NOT** present a `draft` record, and **SHOULD** present a
`proposed` one. Both remain queryable on request.

The distinction is the same one a pull request draws between a draft and an open proposal, and it
exists for the same reason: an author needs somewhere to think without broadcasting. Without it,
the only way to avoid publishing an unfinished thought is not to write it down — which loses
precisely the reasoning that is most worth keeping, at the moment it is most recoverable.

**[REC-104]** A record whose disposition is `declined` **MUST** yield **foreclosure intent**: it
**MUST** be retained and queryable, **MUST NOT** be counted toward any trusted-evidence metric,
and **MUST NOT** be presented as something the authoring team does. A consumer **MUST** be able
to distinguish *decided against* from *never considered*.

**[REC-108]** `superseded` **MUST NOT** be a status. A record is superseded when, and only when,
another record declares a `supersedes` relation naming it (§4.16). Currency **MUST** be derived
from the relation graph, never authored on the record itself.

The `proposed` problem this replaces is real: such a record currently becomes intent
indistinguishable from a decision, at full confidence, counted as ground truth. Marking it open
rather than suppressing it keeps what a team is actively considering visible, which is often the
most urgent information in a corpus.

[REC-104] is the larger correction. A declined decision presently disappears from the graph
entirely, which makes the question that most reliably prevents wasted work — *have we already
considered and declined this?* — unanswerable for exactly the decisions where someone took the
trouble to record the refusal. The asymmetry runs backwards: a rejected *alternative* inside an
adopted record survives as prose, while a deliberately written rejection is deleted. The format
keeps the weakly recorded foreclosures and discards the strong ones.

Three states of a proposition must remain distinguishable: *we decided to*, *we decided not to*,
and *we never considered it*. Collapsing the second into the third discards knowledge that was
explicitly written down. The earlier instinct — that a rejection must never be read as a
commitment — is correct and is preserved by [REC-104]'s presentation rule; the error was
implementing it as deletion.

[REC-108] removes a second source of truth. A status field asserting `superseded` and a
`supersedes` edge asserting the same thing will drift the moment an author writes a superseding
record without revisiting the record it replaces, and nothing can then determine which is
correct. Deriving currency keeps one authority. It also matches how version control already
works: a reverted commit is not flagged, it is referenced by the commit that reverts it, and
whether its effect is current is computed from the history rather than stored on it.

**[REC-141]** The properties [REC-101] determines **MUST** be carried on the parsed record and the
intent node under these key spellings: `deliberation`, `offered`, and `disposition`, each taking the
value of the correspondingly named column. The mark [REC-118] requires **MUST** be carried as
`self_ratification`, a boolean on the record; the corroboration [REC-119] requires **MUST** be
carried as `corroborated`, a boolean on the attribution. This rule assigns spellings only — the
values, and the conditions under which each holds, are [REC-101]'s and are not restated here.

> [REC-101] requires an open record to be marked open, [REC-118] a self-ratification to be marked,
> and [REC-119] an uncorroborated ratification to be marked. An obligation to mark with no key
> spelling lets two conforming implementations both satisfy it and share nothing; this rule fixes
> the spellings.

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

**[REC-105]** A supersession reference that resolves to **more than one** candidate record
**MUST** be dropped, exactly as [REC-044] drops an unresolved one. An implementation **MUST NOT**
select among the candidates by ingest order, filesystem order, recency, or any other tiebreak.

**[REC-106]** A filename **MUST NOT** be treated as carrying an ADR number when the four-digit
run is part of a date. A dated filename of the form `YYYY-MM-DD-<slug>` **MUST NOT** be
resolvable as `ADR-<YYYY>`.

[REC-106] fixes a defect rather than adding a capability, and the defect is severe because it
produces confident wrong answers rather than absences. Where target resolution takes the first
four-digit run in a filename, every dated record captured in a given year registers under the
same key — so a reference intended for one decision resolves to an unrelated record that merely
shares a year, chosen by ingest order. A reference to a decision about connection pooling can
resolve to a decision about logging, and the resulting edge is indistinguishable from a correct
one.

Together [REC-105] and [REC-106] state the general principle: **an ambiguous reference is an
absent reference.** A format may decline to answer. It may not guess and present the guess as
fact.

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

**[REC-135]** **Emitter completeness.** An emitter **MUST** be able to render every field a
parser yields (§4.5–§4.17). A field that can be parsed and cannot be rendered is a defect in this
section, not an accepted limitation, and adding a parseable field without a corresponding
rendering **MUST** be treated as an incomplete change.

**[REC-136]** **Status provenance.** The value rendered on the `**Status:**` line **MUST** be the
record's own status. Where a record has no status ([REC-101], *unstated*), the line **MUST** be
omitted entirely. An emitter **MUST NOT** substitute a default, and in particular **MUST NOT**
emit `accepted` for a record whose status is absent or is anything else.

> [REC-136] guards the most severe round-trip failure a format can have. Every worked example shows
> `Accepted`, so an emitter told to render a status line and not told *which* will hard-code it — and
> a `rejected` record then round-trips to `accepted`: one save turns "we decided against this" into
> "we do this", the inversion [REC-032] and [REC-104] exist to prevent.
>
> [REC-135] addresses the cause rather than the instance. A rendering section written against the
> sections that existed when it was written lets a format read records it cannot write, and every
> later extension inherits the defect unless a rule forbids it. Stating emitter completeness as a
> requirement makes the omission a conformance failure instead of an oversight nobody is
> responsible for noticing.

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

**[REC-137]** Where a record carries the corresponding field, an emitter **MUST** render each of
these sections, in this order, after `## Decision` and before `## Alternatives considered`:

| Section | Rendered when | One item per line, as |
|---|---|---|
| `## Governs` | `governs` is non-empty | `- <artifact reference verbatim>` |
| `## Relations` | `relations` is non-empty | `- <relation> <identifier>` |
| `## Attribution` | `attribution` is non-empty | `- <role> <kind>:<id>[ on <date>]` |
| `## Assumptions` | `assumptions` is non-empty | `- <claim>[ (review by <date>)][ (expires: <condition>)]` |
| `## Evidence` | `evidence` is non-empty | `- <method>[: <qualifier>]` |

**[REC-138]** An emitter **MUST** omit any of these sections entirely when its field is absent or
empty, and **MUST NOT** emit a placeholder for it ([REC-054]).

**[REC-139]** An emitter **MUST** render the `**Id:**` line, adjacent to `**Status:**` and
`**Date:**`, when the record carries an identifier. Dropping it would defeat [REC-076] and
[REC-076], whose whole purpose is an identifier that survives revision.

#### 4.10.1 The placeholder rule

**[REC-054]** A `(none recorded)` placeholder **MUST** be emitted only for a section where the
absence of content is itself an answer — "we considered the question and there was nothing to
list". It **MUST NOT** be emitted for a section whose absence means "nobody was asked". An optional
section added by a vocabulary extension (§7) **MUST** therefore be omitted entirely when it has no
content, unless the first condition applies.

This distinction is normative, not stylistic. `## Alternatives considered` with `(none recorded)`
honestly says *we looked and there were none*. A section rendered the same way for evidence,
provenance, or any other field a human may simply never have been prompted for would state a false
claim about the record's own completeness. A record must not lie about what it knows about itself.

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

**[REC-131]** A directory ingest **MUST** consider exactly those entries in the directory whose name
ends in `.md` and does not begin with `.`. Every other entry — including the reserved bare `Whyfile`
([REC-001]) — is **not a candidate** and contributes nothing. An implementation **MAY** descend into
subdirectories, and where it does it **MUST** apply this same rule at every level. A candidate that
fails [REC-008] is ignored without error ([REC-007]).

> The consequence of an unbounded candidate set is testable rather than theoretical: an extensionless `Whyfile` whose body is a syntactically valid decision record parses
> as one, so an implementation that feeds every file to the parser produces two nodes where one is
> correct — and [REC-001] requires that file to mean nothing.
>
> The `.md` filter is what makes [REC-001]'s reservation self-enforcing rather than a special case an
> implementer has to remember. Recursion is left a MAY because [REC-057] already forbids inferring
> anything from a record's location, so depth cannot change a parse.

#### 4.11.1 Slug derivation

**[REC-058]** A slug **MUST** be derived from its source text by:

1. lowercasing;
2. replacing every run of characters outside `[a-z0-9]` with a single `-`;
3. stripping leading and trailing `-`.

The resulting alphabet is exactly `[a-z0-9-]`, so the slug **MUST NOT** contain a glob
metacharacter. Implementations **MAY** rely on that property when constructing [REC-067]'s lookup
pattern.

**[REC-059]** A slug **MUST** be bounded at 60 characters.

**[REC-060]** Truncation **MUST** land on a word boundary: truncate to the bound, then, if the
result contains a `-`, drop everything from the last `-` onward, then strip trailing `-`.

> Hard-cutting mid-word produced records ending in fragments — `…existing-error-classe.md` — which
> read as permanent typos in a directory humans scan by eye. The word-boundary rule is cosmetic in
> effect and load-bearing in adoption.

**[REC-061]** If the first word alone exceeds the bound, the slug **MUST** be hard-cut. A slug must
be bounded; this is the only case where a mid-word cut is permitted.

**[REC-062]** A slug that reduces to the empty string **MUST** become the literal `decision`.
This applies when the question is absent, empty, or reduces to an empty slug; an implementation
**MUST NOT** fall back to a slug derived from the chosen option.

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
`<today>-<question-slug>.md`, using [REC-062]'s literal `decision` for an absent or empty question
and never a chosen-derived fallback.

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

**[REC-121]** The four inputs **MUST** be joined by exactly `::` with **no surrounding
whitespace**.

**[REC-122]** The **intent kind** component is the kind of the **node**, and **MUST** be exactly
`decision` or `assumption`. It is **not** the record kind of [REC-009]: a record whose H1 is an
ADR form still produces a **decision node**, and an implementation **MUST** hash `decision` for
it. `adr` **MUST NOT** appear in an identity.

**[REC-123]** The identity **MUST** be `intent_` followed by the first **12** characters of the
**lowercase hexadecimal SHA-1** digest of the joined string encoded as UTF-8.

**[REC-124]** Only the label component is normalized ([REC-072]). The source path is
canonicalized per [REC-073]–[REC-074]; the source location **MUST** be hashed as it appears,
without normalization.

For a decision node, source location and label are both the record title, and intent kind is
`decision`. For an assumption node they are derived from the claim, and the kind is `assumption`.

**[REC-127]** For an **assumption node**, the source location and the normalized label are both
derived from the **claim as [REC-038] yields it** — the claim after the review-date and expiry
strippings, whitespace-collapsed and trimmed of spaces and periods. Both components take that text
verbatim; [REC-124] then normalizes only the label. `review_by` and `expiry` are **not** identity
inputs.

> This is the exact analogue of the decision node, where source location and label are both the
> record title. The last sentence is load-bearing: if the stripped fields were inputs, editing a
> review date would fork the node — the harm [REC-073] and [REC-076] exist to prevent, reached
> through a field whose whole purpose is to be revised.

[REC-121]–[REC-124] pin the digest completely because an identity that is derived, exact and
load-bearing forks silently the moment two implementations hash differently: [REC-073]'s rationale
is that hashing the wrong *spelling* of a path forks one node, and hashing with a different
*algorithm* forks every node in the corpus.

[REC-122] names the **node** kind, not [REC-009]'s record kind: `adr` and `decision` appear under a
column headed "Kind", and an implementer who hashed that value would produce a different identity
from one who hashed `decision` or `assumption`. Only one reading can be correct.

> **On SHA-1.** It is specified here because it is what existing corpora already contain, and
> changing it would fork every identity in every deployed record — precisely the harm these rules
> exist to prevent. It is used as a **content identifier, never as a security primitive**:
> nothing in this format relies on collision resistance, and an identity is not a signature. The
> 12-character truncation gives 48 bits, which is ample where corpora hold thousands of nodes
> rather than millions; an implementation encountering a collision **MUST** report it rather than
> silently merge the nodes.

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

### 4.13 Record identifier

**[REC-075]** A record **MAY** carry an identifier in the inline field form, `**Id:** <value>`,
placed with `Status` and `Date`.

**[REC-159]** A record **MAY** carry its date in the inline field form, `**Date:** <value>`. The
label is matched case-insensitively and only the first such line outside a fenced block
([REC-158]) counts. A parser **MUST** yield `date` when the value is a full ISO-8601 calendar date
(`YYYY-MM-DD`), or begins with one followed by whitespace — `2026-09-08 (revised)` yields
`2026-09-08`, while `2026-09-08(revised)` yields nothing — and **MUST** leave `date` absent
otherwise. A malformed value **MUST NOT** be repaired or widened, as [REC-129] treats an
attribution date.

> The emitter has rendered this line since [REC-047]; the parser side was never stated, so a reader
> could not know whether `**Date:** March` yielded a date, a string, or nothing. Absent is the
> honest answer, and the trailing-annotation tolerance exists because people write one.

**[REC-076]** An identifier, once written, **MUST NOT** be regenerated, and **MUST NOT** be
derived from any mutable part of the record. In particular it **MUST NOT** be derived from the
title, the body, or the filename. It **MUST** remain stable across an edit to every other part of
the record; correcting a title retains the identifier.

**[REC-078]** An identifier **MUST** be unique within a corpus. Two records sharing an
identifier is an error; neither **MUST** be treated as the referent.

Node identity (§4.12) and the record identifier answer different questions. The node identity is
content-derived and exact: it names *this* record as it is now, and it necessarily changes when
the content it hashes changes. The identifier is *citational*: it survives revision so that other
records can refer to this decision across its lifetime. A format with only the first cannot be
cited; a format with only the second cannot detect that anything changed. Both are required, and
conflating them is what makes an in-place title correction silently fork a node and dangle every
reference to it.

### 4.14 Attribution

Attribution is a **relation**, not a field. A record routinely involves more than one actor in
more than one capacity, and a single-valued author field cannot represent that without
misreporting it.

**[REC-079]** A record **MAY** carry an `## Attribution` section, one attribution per list item,
in the form `<role> <kind>:<id> [on <date>]`.

**[REC-080]** `<kind>` **MUST** be one of exactly `human` or `agent`. `<role>` **MUST** be one of
exactly `drafted`, `decided`, or `ratified`. Both sets are closed; adding to either requires a
version marker (§7).

**[REC-081]** A record **MAY** carry any number of attributions, including several sharing a
role. An absent attribution **MUST** be read as *unrecorded*. It **MUST NOT** be defaulted to
`human`, and **MUST NOT** be inferred from any other field.

**[REC-128]** An **actor** is the ordered pair `(kind, id)` taken from an attribution's `<kind>:<id>`
term. Two actors are the same actor **if and only if** both components are equal, compared as
written — no case folding, and no trimming beyond [REC-079]'s parse. [REC-118]'s self-ratification
check **MUST** compare the pair.

> The pair rather than the bare id, because `human:alex` and `agent:alex` are the common
> machine-assisted shape §4.14 describes — a person and the agent working on their behalf. Comparing
> bare ids would report a self-ratification that did not occur, and [REC-118] is the only entitlement
> check the format can make from the record alone. A false positive there is worse than none.

**[REC-129]** An attribution whose date is present but is not a full ISO-8601 calendar date
([REC-117]) **MUST** be yielded with its date **absent**. The malformed value **MUST NOT** be
yielded, widened to a valid date, or repaired, and the attribution itself **MUST NOT** be dropped.

> Dropping the attribution would discard *who did what* because *when* was mistyped, and [REC-120]
> already establishes that a weak attribution is retained rather than deleted. Absence of the date
> then means what absence means everywhere else in this format — not recorded ([REC-081],
> [VER-005]).

**[REC-115]** The roles are distinct and **MUST NOT** be conflated. `drafted` names who composed
the record; `decided` names who chose among the alternatives; `ratified` names who accepted it
through a review process.

**[REC-116]** Where a record carries an `## Attribution` section, ratification governs its
provenance tier and the kind-based assignment of [PROV-005]/[PROV-006] **MUST NOT** be applied.
Where a record carries no attribution, the kind-based assignment applies unchanged.

**[REC-118]** A ratification is **self-ratification** when the same actor also carries the role
`drafted` or `decided` on that record. Self-ratification **MUST** be marked, **MUST NOT** promote
provenance, and **MUST NOT** be discarded.

**[REC-119]** A ratification alone **MUST NOT** promote a record to `authored`. Promotion
**MUST** additionally require **corroboration** — evidence, external to the record, that the named
actor accepted it and was entitled to. An implementation unable to corroborate **MUST** mark the
ratification *uncorroborated*, **MUST NOT** promote, and **MUST** leave the record at `captured`.

**[REC-120]** A self-ratification and an uncorroborated ratification **MUST NOT** be discarded.
Each records that someone asserted acceptance, which is information about the record even when it
is not evidence for its tier.

This specification does not define what corroboration consists of; that depends on where a corpus
lives. A review approval recorded by a hosting platform, a signature, or an attestation from a
system that observed the acceptance would each serve. What the format fixes is that **the
assertion alone is never sufficient**.

The reason is the standing one: this format records *who claimed what*, and never adjudicates
whether a claim is true. "X ratified this" is a claim about the world. The format can carry it
faithfully; it cannot settle it, and a format that treated the assertion as the fact would be
doing exactly the detection it refuses to do everywhere else.

**[REC-118] exists because the mechanism it constrains is one this specification introduced.**
Before ratification existed, the top tier was reached by typing an `# ADR-` heading — trivially
assertable, but *transparently a convention*, and read as one. A line reading `ratified
human:me` is equally assertable and looks like a record of verification. A claim that appears
verified while resting on nothing is more dangerous than one that is visibly conventional, so
adding the mechanism without the constraint would have been a regression wearing the appearance
of rigour.

Self-ratification is worth singling out because it is the one abuse checkable **from the record
alone**: it requires no external data, no inference, and no classifier — only the observation
that one identifier appears in two roles. It is the four-eyes principle, and it is the only part
of entitlement the format can enforce by itself.

Declining to promote is **not** enforcement in the sense the fences bound. The record is still
ingested, still queryable, still intent, and still counted among the golden tiers, because
`captured` is itself a trusted class ([PROV-010]). Nothing a person wants to do is blocked. The
system simply declines to assert something it cannot support — and the fence against blocking
governs whether a control obstructs a user, not whether an implementation must believe every
claim made to it. The distinction matters because the fence's own reasoning turns on
*heuristics* having false positives, while [REC-118] is structural and has none.

A consequence worth stating plainly: in a corpus with no independent reviewer — a single
maintainer, or an agent working alone — no record reaches `authored`, and that is the correct
outcome rather than a penalty. `authored` means a review process accepted the record. Where no
such process exists, claiming the tier would be false, and the honest tier is `captured`, which
already counts as trusted evidence.

**[REC-117]** Each attribution **MUST** carry its own provenance (§5.5) and **MAY** carry a date.
Where a date is present it **MUST** be a full ISO-8601 calendar date.

Attribution is not provenance. Provenance says what *kind of source* a claim came from and
therefore how much it is worth; attribution says *who* did what, in what capacity, and when. A
format that promises attribution while recording no attributee is incomplete in the middle of its
own central commitment.

The multiplicity is not a hypothetical refinement. The common case for machine-assisted capture
is an agent composing a record — options, rationale, alternatives — and a human choosing among
them: two actors, two roles, one record. A single author field must misreport one of them, and
will tend to misreport in whichever direction flatters the writer. Recording both is also what
makes an actor-centric history answerable at all, since a scalar buried on each record cannot be
traversed from a person back to their decisions.

[REC-116] gives the tier an act to follow. The distinction between `captured` and
`authored` is, by the tier table's own words, whether a review process accepted the record — yet
nothing recorded a review ever happening, so the strongest tier was earned by how a file was
named. Ratification is an act with an actor and a date, and the tier now follows the act rather
than the naming.

[REC-081]'s absence rule follows the logic of the provenance default (§5.2): defaulting an
unknown to the stronger reading silently promotes unattributed material.

Attribution composes with declared scope and with time to answer the question audit actually
asks — *was this decided by someone entitled to decide it, at the time they decided it?* That
question is unanswerable from a scalar field, because it needs the capacity as well as the
identity, and because authority itself moves between people.

### 4.15 Governs — declared artifact scope

**[REC-082]** A record **MAY** carry a `## Governs` section listing the artifacts the decision
governs, one per list item. List markers are stripped per [REC-022] and empty items dropped per
[REC-025], but an item's text **MUST** otherwise be taken **verbatim**: the emphasis-stripping
and whitespace normalization of [REC-023] **MUST NOT** be applied.

> **Why this section departs from the shared list rules.** [REC-023] removes every `**` sequence,
> which is correct for prose and destructive for a path glob: `src/edge/**/*.py` normalizes to
> `src/edge//*.py`, silently converting a recursive-descent glob into a literal empty path
> segment. Applying it produces broken globs that mis-resolve every declared scope — a failure that
> surfaces as a decision quietly governing nothing, which [REC-086] would report as an empty
> resolution while the actual cause sat in the parser.
>
> The general lesson is worth keeping: a normalization written for human prose cannot be reused
> unexamined on a machine-readable value that shares the document's markup characters.

**[REC-083]** Each item **MUST** be an **artifact reference**. This version defines exactly two
kinds of artifact reference: a **repository-relative path glob**, and a **symbol reference**
([REC-151]). Other kinds are reserved and undefined; an implementation **MUST NOT** invent one,
and adding a kind requires a version marker (§7).

**[REC-151]** A **symbol reference** **MUST** be written `<path>#<symbol>` — a repository-relative
path carrying no glob metacharacter, a single `#`, and a non-empty symbol name — and resolves to
that symbol within that file. An item containing no `#` **MUST** be read as a path glob. An item
containing a `#` **MUST** be read as a symbol reference **even when it is malformed**, so that a
mistyped reference reports through [REC-086] rather than silently degrading into a glob. [REC-086]
governs the unresolved case unchanged.

> **Why a second kind, and why this one.** The path glob was the only kind specified because no
> second one was needed yet. In-code rationale is the rationale practice observed at scale, and it
> explains a *symbol*, not a directory; a declared scope that could not name one could not describe
> the commonest thing a decision governs.
>
> The disambiguation rule reads a malformed reference as a malformed *symbol* reference rather than
> as a glob. That looks like the unhelpful reading and is the safe one: a symbol reference is a
> legal path string, so the alternative is for `src/edge/handler.py#validte_request` to become a
> glob matching nothing, and to surface under [REC-086] as *scope that has gone stale* — a typo
> wearing the costume of decay. Reading it as a symbol reference reports the same empty resolution
> with the reference kind intact, which is what makes the report actionable.
>
> [REC-086] gains rather than loses precision here. A symbol reference that stops resolving is a
> rename detector; a glob that stops matching is a much blunter instrument for the same job.

#### 4.15.1 Path glob forms and resolution

**[REC-152]** A path glob item **MUST** be read as exactly one of three forms, decided by its text
after [REC-153]'s normalization:

| Form | Written as | Resolves to |
|---|---|---|
| **file** | a repository-relative path with no trailing `/` and no glob metacharacter | the artifact at exactly that path, or nothing |
| **directory** | a repository-relative path ending in `/` | every artifact whose path begins with that prefix, at any depth |
| **glob** | an item containing any of `*`, `?`, `[`, `{` | every artifact the pattern matches, where `*` and `?` **MUST NOT** match a `/` and `**` matches across separators |

The forms are tested in this order: a trailing `/` first, then the presence of a glob
metacharacter, then exact path equality — so `src/*/` is a **directory** whose prefix contains a
literal `*`, not a glob. A **file** form that names a directory — a bare directory name with no
trailing `/` — names no artifact and **MUST NOT** be read as governing the directory's contents. A **glob** that cannot be
compiled **MUST** resolve to zero artifacts. In every case a zero resolution is reported under
[REC-086].

> **Why three forms and not a smarter reader.** The declaration failure this rule answers was
> measured before it was written: when sessions were asked to declare a scope, every one did, and a
> third of the declarations resolved to nothing under the reader's rule — paths that did not exist,
> and bare directory names with no glob. Agents think in directories; the reader thinks in paths. The alternative — reading `src/edge` as `src/edge/` when a directory of that
> name exists — makes the meaning of an item depend on the tree at the moment it is read, so the
> same declaration governs one set of files today and a different set after a rename. A trailing
> slash costs one character and keeps the meaning in the text. The glob rule follows the same
> principle from the other side: a `*` that crosses a separator turns `src/*.py` into a recursive
> claim nobody wrote.

**[REC-153]** Before classification under [REC-152] and [REC-151], a reader **MUST** derive the
reference from the item text [REC-082] yields, in this order:

1. where the item contains a code span, the contents from its first backtick to its last are the
   reference and everything outside them is annotation;
2. otherwise, where the item ends in `)`, the parenthetical from its last `(` to the end is
   annotation and is removed;
3. a leading `./` is removed;
4. an item that is empty, or contains whitespace, after steps 1–3 is **not an artifact reference**
   and **MUST** resolve to zero artifacts.

An implementation that resolves at file granularity ([REC-155]) drops the symbol suffix — the
first `#` and everything after it — between steps 2 and 3, so that a reader implementing this
rule alone and one implementing [REC-155] agree on the match set for every item.

A writer **SHOULD** emit the bare reference, with no code span and no annotation; the tolerance
exists for readers and is not a second syntax.

> [REC-082] yields the item verbatim so that a glob's `**` survives the prose normalizer. This rule
> is the other half: what a *reader* does with what it was given. Models writing a `## Governs`
> item unprompted wrap the path in a code span or follow it with a reason in parentheses, and a
> reader that matches those literally resolves nothing and reports a decision that governs
> nothing. Step 4 is the limit of the tolerance: prose that mentions a path — "everything under
> `src/` except the vendored tree" — declares no scope, and guessing one would push a decision
> onto files nobody scoped it to.

**[REC-154]** An artifact reference is repository-relative. A writer **MUST NOT** begin an item
with `/`. A reader **MUST NOT** interpret a leading `/` as the repository root: an item beginning
with `/` matches no repository-relative path, resolves to zero artifacts under [REC-152], and is
reported under [REC-086].

> Stated on both sides because the two failures differ. A writer who means the repository root
> and writes `/src/` has written a path no repository-relative artifact carries; a reader that
> quietly strips the slash has made the declaration mean something its text does not say, and the
> next reader — a different implementation, or a person — cannot tell it was repaired. The empty
> resolution is visible; the repair is not, which is [REC-086]'s argument applied one rule earlier.

**[REC-155]** An implementation that resolves scope at **file** granularity **MAY** resolve a
symbol reference ([REC-151]) to the file it names, by the path before its `#`. The reference
**MUST** still be yielded and reported as a symbol reference; only its resolution is coarsened.

**[REC-156]** [REC-152]–[REC-155] govern declared scope items. A checker that resolves **prose
referents** in a record's other sections — a path mentioned in a rationale, cited from a sub-root,
or given as a bare filename — **MAY** resolve them more tolerantly, but tolerance **MUST NOT**
confer governance: a referent resolved from prose is evidence about the record's currency, never
a declared scope binding, and [PROV-013] and [PROV-015] apply to it as to any inferred edge.

> Two inputs, two rules. The declared grammar exists so that a writer can be held to it; the
> tolerant resolver exists because the records already in the world were not written to any
> grammar — measured across external corpora, more than half name no locating referent at all —
> and a checker that read the rest strictly could measure nothing. Letting the tolerant rule leak
> into governance would be the phantom-intent failure this format exists to prevent.

**[REC-084]** An absent `## Governs` section **MUST** be read as *scope not declared*. It
**MUST NOT** be read as *governs nothing*.

**[REC-086]** An artifact reference that resolves to **zero** artifacts **MUST** be reported as a
distinct, named state — neither silently dropped nor treated as an error.

[REC-086] is the section's most useful rule and the least obvious. A declared scope can go stale:
code moves, and a glob outlives the thing it named. The objection this invites is that a stale
declaration is worse than an honest inference, because it carries the authority of something a
human wrote. The answer is that **a declaration that matches nothing is mechanically detectable,
and a stale inference is not** — an inference that has quietly stopped being true simply
disappears, while an empty resolution announces itself. Requiring the empty case to be reported
converts the format's most-feared failure mode into its best staleness signal.

[PROV-013] is what moves a decision's binding to its code out of the weakest evidence tier. An
implementation that *infers* which code a decision governs produces `reconstructed` intent, which
[PROV-001] says a consumer must never present as something a human decided. A declared scope was
written by whoever wrote the record, and is worth exactly what the record is worth.

### 4.16 Relations

**[REC-087]** A record **MAY** carry a `## Relations` section, one relation per list item, in the
form `<relation> <identifier>`.

**[REC-088]** `<relation>` **MUST** be one of exactly `supersedes`, `refines`, `constrains`,
`motivated_by`, `trade_off_against`, or `contradicts`. The set is closed; adding a relation
requires a version marker (§7).

**[REC-089]** `<identifier>` **MUST** be a record identifier ([REC-075]) or an ADR number.

**[REC-090]** A relation whose target cannot be resolved **MUST** be dropped silently, per the
same reasoning as [REC-044] — a corpus may be partial.

**[REC-091]** A relation whose target is **ambiguous** — resolving to more than one candidate
record — **MUST** be dropped, and **MUST NOT** be resolved to any one of them. An implementation
**MUST NOT** select by ingest order, recency, or any other tiebreak.

[REC-091] is the single most important rule in this section, because it is the only one
that stops the format from asserting something false. An unresolvable reference produces no edge,
which is a safe failure — a reader sees nothing and knows nothing. An *ambiguous* reference
resolved by tiebreak produces a **wrong** edge that is indistinguishable from a correct one, and
it inherits the authority of whatever tier the declaring record carries. Silence is recoverable;
a confident wrong answer is not.

Prose supersession ([REC-040]–[REC-044]) remains valid and is unaffected. `## Relations` is the
declared form; neither supersedes the other.

### 4.17 Evidence

**[REC-093]** A record **MAY** carry an `## Evidence` section, one entry per list item, in the
form `<method>: <qualifier>`, where the qualifier is optional.

**[REC-094]** `<method>` **MUST** be one of exactly `grep`, `diff`, `executed`, `read`, or
`traced`. The set is closed; an unrecognized method is a validation error at capture time, not a
silently unflagged value.

**[REC-130]** A parser reading a record whose `## Evidence` entry names a method outside [REC-094]'s
set **MUST** drop that entry and **MUST NOT** yield the value as a method. Other entries in the
section parse unchanged, and the record still parses: an evidence defect is not a record-gate defect
([REC-008]).

> [REC-094] states its failure mode for the **write** path only — a validation error at capture time
> — which left an implementer reading an existing file to choose between yielding a fifth method
> (silently widening a closed set that [VER-003] says needs a version marker) and dropping it.
>
> The alternative — retaining the entry with its method marked unrecognized — is defensible and
> preserves more information, but it needs a second field, a rule for what consumers do with it, and
> an answer to what happens when that value is later admitted to the set. Drop is the smaller rule.
> Note what it costs: the qualifier text is lost with the entry, and a record whose author used a
> near-miss spelling reads as having recorded nothing about method, which [REC-096] then forbids
> anyone from flagging.

**[REC-095]** An entry **MAY** cite the deliberation that produced the decision, as a reference
to where that deliberation occurred. A citation **MUST** be a reference. An implementation
**MUST NOT** embed deliberation content in the record, and this specification defines no field
for doing so.

**[REC-096]** A record with no `## Evidence` section records nothing about method. It
**MUST NOT** be read as *no evidence existed*, and **MUST NOT** be flagged on that basis.

Evidence and provenance are orthogonal, and the distinction is easy to lose. Provenance answers
*how strong is this claim*; evidence method answers *how did the author come to make it*. The
second is what tells a later reader **how far a claim can be stretched** — a conclusion recorded
as "executed, one command" is visibly unable to support a claim about every command, and a reader
sees that without re-running anything.

[REC-095] draws a deliberate line. Deliberation is how intent forms and is therefore genuinely
valuable as an evidence chain, but it is not itself a claim and must not become intent: ingesting
it would fill a corpus of decisions with tentative positions and abandoned reasoning, and a
reader could no longer distinguish *we decided this* from *someone said this while thinking*.
Pointing rather than embedding also keeps a conforming implementation from becoming the store of
record for conversational content, which carries privacy exposure wholly disproportionate to the
value of the citation.

The corollary is worth stating plainly for implementers: where deliberation occurred somewhere
durable, cite it; where it occurred somewhere ephemeral, **do not cite it at all — distil the
reasoning into the record's rationale.** A citation that resolves to nothing is worse than no
citation, because it presents as evidence and yields none.

### 4.18 Currency, derived by reachability

**[REC-111]** A record's **currency** — whether the decision it carries is still live —
**MUST** be derived from the relation graph. It **MUST NOT** be authored on the record.

**[REC-112]** Where [REC-101]'s **Currency defined** column is *yes*, a record is **historical**
when at least one other record declares a `supersedes` relation naming it, and **current**
otherwise. Where that column is *no*, the record has no currency. This rule determines *which*
value applies; [REC-101] determines *whether* one applies at all.

**[REC-113]** Supersession **MUST** be applied transitively. Where A supersedes B and B
supersedes C, both B and C are historical.

**[REC-114]** A record participating in a supersession **cycle** **MUST** be reported as having
**indeterminate** currency. An implementation **MUST NOT** resolve a cycle by ingest order,
recency, or any other tiebreak, and **MUST NOT** traverse one without termination.

Currency is computed the way version control computes whether a change is still in effect: not
by reading a flag on the change, but by walking the graph from what is current. A reverted commit
carries no marking; it is referenced by the commit that reverts it, and its status follows from
the history rather than from an assertion inside it.

The practical gain is that currency cannot go stale. An authored `superseded` flag records what
was true when someone last remembered to edit that file; a derived one records what is true now,
and updates itself the moment a superseding record is written.

[REC-114] applies the ambiguity principle of [REC-091] and [REC-105] to a third case. A cycle is
a corpus that contradicts itself about what replaced what, and there is no defensible way to pick
a winner. Reporting indeterminacy tells a reader something true; picking one tells them something
that may be false and looks identical to something known.

---

## 5. Provenance vocabulary

Provenance is the format's **primary trust axis**. It answers "how do we know this?", and it is the
field a consumer must consult before treating recorded intent as ground truth.

### 5.1 The tiers

**[PROV-001]** Provenance **MUST** be one of exactly five values. The set is closed; an
implementation **MUST NOT** mint a sixth without a version marker (§7, [VER-003]).

| Tier | What it means | What it is worth |
|---|---|---|
| `authored` | Ingested verbatim from a **reviewed, ratified** human decision record — an ADR. | Ground truth. The strongest claim the format can carry: a human wrote it *and* a review process accepted it. |
| `captured` | Ingested verbatim from a decision record written **at the moment of choosing**. | Ground truth, human-written, but not yet reviewed or ratified. Highest-fidelity provenance available, because it was recorded when the reasoning was still in someone's head — but it carries one person's word, not a process's. |
| `attested` | Human rationale written as an **aside** — a commit trailer, an inline `# why:` comment, a pull-request body. | Human-written and bound to a specific diff, so it outranks anything inferred. Less formal than a record: it was never structured as a decision, so it rarely names alternatives. This is the zero-workflow tier every repository already has on day one. |
| `reconstructed-then-ratified` | **Machine-originated** — reconstructed from code, history or documentation, or drafted by an agent for a decision it made — and then **read, edited as needed, and approved by a person**. | The highest tier a machine-originated claim can reach. A human judgment was spent on it and is not discarded; but nobody wrote it at the moment of deciding, so it ranks below every human-written tier. |
| `reconstructed` | **Inferred** from code or documentation by an automated pass. | The weakest tier. Plausible, useful for navigation, and never evidence. A consumer **MUST NOT** present reconstructed intent as something a human decided. |

> **Why a fifth tier.** A record a machine reconstructed and a person then approved is not `authored` — nobody wrote it when the decision was made — and filing it as `reconstructed` throws away the one scarce thing the system spent on it, a human's reading. Collapsing it either way is the phantom-intent failure from opposite sides: `authored` lets a reconstruction outrank a record, `reconstructed` hides that a person vouched for it. It sits below `attested` because an aside a person wrote at the time is still first-hand; a ratified reconstruction is second-hand, however carefully read.

### 5.2 Ordering

**[PROV-002]** The tiers **MUST** be totally ordered, highest trust first:

```
authored  >  captured  >  attested  >  reconstructed-then-ratified  >  reconstructed
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

**[PROV-005]** An ADR record ([REC-009]) carrying no `## Attribution` section **MUST** yield
`authored` intent.

**[PROV-006]** A decision record ([REC-009]) carrying no `## Attribution` section **MUST** yield
`captured` intent.

**[PROV-021]** Where a record carries an `## Attribution` section and at least one `drafted` or
`decided` actor is `human`, its tier **MUST** be determined by ratification ([REC-116],
[REC-119]) and **MUST NOT** be determined by record kind. A record with attribution but no
corroborated ratification **MUST** be `captured`, whatever its heading form.

**[PROV-022]** Where a record carries an `## Attribution` section naming at least one `drafted`
or `decided` actor and **every** such actor is `agent`, the record is machine-originated and the
drafter's kind is a **ceiling**: with a corroborated ratification ([REC-119]) by a `human` actor
the record **MUST** be `reconstructed-then-ratified`; without one it **MUST** be `reconstructed`.
Ratification **MUST NOT** promote such a record to `authored` or `captured`. A record of this kind
**SHOULD** carry an `## Evidence` entry citing what it was reconstructed from ([REC-095]).
Actors are compared as [REC-128] compares them, kind and id together: `drafted agent:x` and
`ratified human:x` are different actors, so that ratification is corroborated — the person who
ran the tool and then approved its draft is the ordinary case, not a self-ratification. The tier
is named for its commonest case; the rule is about who originated the claim, and it applies
equally to a record an agent decided and wrote at the moment.

> The tier follows from who did what, which attribution already states, so re-parsing the same
> lines yields the same answer and no new vocabulary is needed. The alternative — a separate marker
> saying "this was reconstructed" — could disagree with the attribution beside it, and the format
> would then have to adjudicate between two statements about the same fact. The ceiling is the
> point: a person approving a machine's draft is a real judgment and is kept, but it cannot turn
> a reconstruction into something written at the moment of deciding. Where a human `decided`,
> [PROV-021] applies unchanged; that is the machine-assisted capture §4.14 describes, and it is
> `captured` because a person chose.

[PROV-005] and [PROV-006] are retained for records that predate attribution, and they are a
**compatibility affordance rather than an endorsement**. An `# ADR-` heading is a *convention*
signalling that a review happened; it is not a record of one, and nothing about it is verifiable.
Existing corpora keep their tiers and need no migration, while any record that states its
attribution is judged on what it states.

The direction of the override matters. Explicit attribution is stronger evidence than a naming
convention, so where both are present the explicit form governs — including when it results in a
*lower* tier than the heading alone would have given. An ADR-headed record whose only
ratification is self-asserted is `captured`, and it should be: the heading claims a review the
record's own attribution shows did not independently occur.

**[PROV-007]** An assumption node **SHOULD** inherit the provenance tier of the record that
declared it.

> An implementation that minted every assumption as `authored` would invert trust: an assumption
> would outrank the decision that stated it, and unreviewed assumptions would count as reviewed
> ground truth.

**[PROV-008]** Intent ingested from a record **MUST** carry a numeric confidence of `1.0`. The
record *is* the evidence; there is nothing to be uncertain about at ingest.

**[PROV-009]** An implementation **MUST NOT** conflate provenance with a numeric confidence score
or with any string confidence label from an extraction pipeline. They are orthogonal axes:
provenance says *who said it*, confidence says *how sure the extractor was*. Filtering and merging
**MUST** use the numeric score only; trust decisions **MUST** use provenance only.

### 5.4 Trusted evidence classes

**[PROV-010]** The **golden tiers** — the evidence classes that count as trusted — **MUST** be
exactly `{authored, captured, attested, reconstructed-then-ratified}`. A ratified reconstruction
counts because a person accepted it; an unratified one never does.

**[PROV-012]** A trust metric **MUST NOT** blend tiers into a single scalar without also reporting
the per-tier breakdown. A blended number is the one output that makes a corpus of inferences look
like a corpus of decisions.

### 5.4.1 Disposition is not a trust tier

**[PROV-017]** Disposition (§4.6.1) and provenance **MUST** be treated as independent axes. A
declined record retains the provenance tier its source earns; being declined **MUST NOT** lower
it, and carrying a strong tier **MUST NOT** make a foreclosure read as a commitment.

**[PROV-018]** Foreclosure intent **MUST NOT** be counted toward any trusted-evidence metric
([PROV-010]), regardless of its provenance tier.

**[PROV-019]** A result containing intent **MUST** expose disposition, so a consumer can
partition commitments from foreclosures without inspecting record text.

**[PROV-020]** A consumer **MUST NOT** present foreclosure intent as an answer to what the
authoring team *does*. It **MAY** present it as an answer to what the team **considered and
declined**.

These are different questions and the format must not let them blur. *What do we do about
authentication?* is answered by commitments. *Have we considered OAuth before?* is answered
largely by foreclosures, and answering it is the mechanism by which a team stops relitigating
settled ground.

The interaction needs stating because the two axes genuinely compose. A rejection written in a
reviewed record is `authored` — the strongest tier the format has — and a naive ranking would let
it outrank an adopted decision recorded at a weaker tier, producing a result that reads as *this
is what we do* for something explicitly refused. Provenance says how much to believe that the
record says what it says; disposition says what it says. A high-confidence account of a refusal
is still a refusal.

This specification does not prescribe ranking (§1.4). [PROV-019] is what makes a conforming
implementation *able* to rank correctly, and [PROV-020] is the constraint on presentation that
holds however it ranks.

### 5.5 Provenance of relationships

**[PROV-013]** An **edge** — any relationship between two intent nodes, or between an intent node
and an artifact, including every declared or inferred scope binding and relation object — **MUST**
carry `provenance` determined by **how the edge itself was established**. A declared scope binding
or relation takes the provenance of the record that declares it. An inferred scope binding or
relation **MUST** be `reconstructed`, and an inferred relation **MUST NOT** be presented as a
declared one. An edge's provenance **MUST NOT** be assigned from the tier of a node merely because
the edge connects to that node.

**[PROV-015]** A binding between intent and an artifact **MUST** be `reconstructed` unless it was
declared (§4.15). An implementation **MUST NOT** present an inferred binding at any stronger
tier.

**[PROV-016]** Ordering and trust rules ([PROV-002], [PROV-004]) apply to edges exactly as they
apply to nodes.

Treating provenance as a property of nodes alone is a category error with a concrete consequence.
A relationship is itself a claim — *this decision depends on that one*, *this decision governs
this code* — and it can be asserted by a human or guessed by a heuristic. Those are not equally
trustworthy, and inheriting a tier from a connected node makes them indistinguishable.

The failure this prevents is already observable in practice: an implementation that binds intent
to code with a similarity heuristic at moderate confidence, over nodes that were authored, yields
edges wearing the strongest tier the format has. Every downstream consumer then reads a guess as
a human decision. [PROV-015] makes the tier honest, and §4.15's declared scope is what allows a
binding to legitimately earn a stronger one.

---

## 6. The recall envelope

The one envelope this specification defines is the text that puts the decisions governing a path in
front of the writer about to change it. It is produced at two coupling points: when a path is
first about to be edited, and at the recorded intention before building begins (the **plan-gate**
form). How the text reaches the writer — the JSON a hook returns, a message in a transport, a file
— is the harness's format and is not specified here.

### 6.1 Shape

**[ENV-051]** A recall envelope **MUST** consist of a **preamble** followed by **one section per
record delivered**, in that order. Where no record governs the path, the envelope **MUST** be
empty: no preamble and no sections. Whether nothing governed the path or the implementation could
not resolve it is recorded on the recall line ([INT-011]), not in the envelope.

**[ENV-052]** The preamble **MUST** state four things, in any wording: that recorded decisions
govern the named path; that their author is not present in the session; that they are to be read
before the change is made; and that a departure from one must be said and recorded.

> Structure is normative and wording is not. A harness may localise or rephrase the preamble
> without breaking conformance; what it may not do is drop an obligation. The reference wording is
> one sentence: *Recorded decisions govern `<path>`. They were written by someone who is not in this
> session; read them before changing the file, and if this change departs from one, say so and
> record why.*

**[ENV-053]** Each record section **MUST** begin with a level-2 heading carrying, in order, the
record's title; its status, or the words `status not stated`; its date, or `undated`; and the
record's repository-relative path — `## <title> (<status>, <date>) — <path>` — followed by the
record's decision text. A reader **MUST** be able to attribute every section to a record from its
heading alone.

**[ENV-054]** The decision text in a section **MAY** be bounded, and the bound is
implementation-defined. A truncation **MUST** be visible in the delivered text: a bounded section
**MUST NOT** be a silent prefix of the record's decision text.

> The bound exists because a push that costs more than the edit it accompanies is a cost paid on
> every edit; the visibility rule exists because a reader who cannot tell that text was cut will act
> on half a decision as if it were the whole. A suffix such as `… (see the record)` satisfies it;
> the form of the mark is the implementation's.

**[ENV-055]** In the plan-gate form, the sections **MUST** be preceded by a header naming the count
of records delivered. Where the intention carries no recorded goal, a request for the goal
**MUST** precede that header and every section. The order is normative: the goal request comes
first.

> Agents answer what they see first. A goal request placed after the records is skipped; placed
> before them it is answered.

### 6.2 Absent versus null

**[ENV-038]** A key **omitted** from a JSON object this specification defines — a node, a reserved envelope (Appendix A), or an intent-layer object **MUST** mean *not applicable to this
variant*. An explicit `null` **MUST** mean *applicable, and the value is known to be unavailable*.

**[ENV-039]** An implementation **MUST NOT** use the two interchangeably. Where the spec names a
present-with-null field ([ENV-029], [ENV-037], [ENV-041]), the key **MUST** be present.

### 6.3 Reserved command variants

Appendix A carries the command-shaped result envelopes specified for an earlier implementation.
They are **reserved**: their rules keep their identifiers and text so that an implementation may
adopt one without inventing a shape, and their fixtures are retained but do not count toward
conformance (§9). None is required of a conforming implementation.

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
- Adding a new **command** to the reserved union (Appendix A.2) — an unknown tag is already required to be handled
  ([ENV-008]).

### 7.3 Absence stays honest

**[VER-005]** A change **MUST NOT** re-interpret the absence of a field in existing records as a
claim or retroactively infer a value the record does not carry. Absence means *this was not
recorded* and **MUST** continue to mean that after the change. A wrong inference dressed as data is
worse than an honest gap: the gap is visible and the inference is not.

### 7.4 Scope of the version marker

**[VER-007]** The version marker governs **the record format and the core envelope only**. It does
**not** govern transport attachments ([ENV-043]), storage layouts, index formats, ranking
behaviour, or any other non-goal from §1.4.

**[VER-008]** This document defines the **pre-publication baseline**, and the record format carries
no explicit version marker in that baseline. A record is recognized by its H1 shape alone
([REC-008]). Draft edits that established this baseline are not changes to an earlier public format
and therefore do not trigger [VER-001]. After the baseline is published, [VER-001] governs the first
meaning change; its marker format and migration note are defined in §7.6 and **MUST** be applied
before that change merges.

---

### 7.5 Establishing the baseline

This working draft has not been published as a compatibility contract and has no external
implementer to migrate. Its current status table (§4.6.1), parsed alternative object
([REC-134]), optional sections, core envelope, and provenance rules together define one clean
pre-version baseline. No record-format marker or migration note is owed for the edits that produced
it.

[VER-001] remains the forward rule. Once this baseline is published, a proposal that reinterprets
one of those existing fields, sections, or shapes must apply §7.6's marker and migration before the
meaning change merges. A vocabulary extension remains governed by [VER-002].

### 7.6 The version marker

**[VER-009]** The specification carries a version of the form `MAJOR.MINOR`, stated in its header.
A meaning change ([VER-001], [VER-003]) **MUST** increment `MINOR`. A vocabulary extension
([VER-002], [VER-004]) **MUST NOT** change the version. `MAJOR` is `0` while this document is a
draft and changes only when the format is declared stable; nothing in this section depends on it.

**[VER-010]** Every meaning change **MUST** add one row to the migration table below before it
merges: the new version, the rule ids whose meaning changed, and a **migration note** of one
paragraph stating what a record written under the previous version means under the new one. A
meaning change without a row is not merged.

| Version | Rules | Migration note |
|---|---|---|
| 0.1 | — | Pre-publication baseline ([VER-008]). No record carries a marker; every record reads under this document as it stands. |
| 0.2 | [PROV-001], [PROV-002], [PROV-010], [PROV-021] | A fifth tier, `reconstructed-then-ratified`, is added between `attested` and `reconstructed` and counted among the golden tiers; [PROV-022] assigns it from attribution, and [PROV-021] is narrowed to records with a human drafter or decider. An existing record changes tier only if every drafter and decider it names is an agent — such a record was `captured` or `authored` under 0.1 and is `reconstructed` or `reconstructed-then-ratified` under 0.2, which is the correction the tier exists to make. Every other record keeps its tier: a record written under 0.1 carries one of the four earlier values or none, and [PROV-003] still ranks an absent value as `reconstructed`. A consumer that enumerates tiers must admit the fifth; one that does not is reading a 0.2 corpus under 0.1 and will rank the new tier as `reconstructed`, which is the safe direction. |

**[VER-011]** A record **MAY** declare the format version it was written to, as an inline field
`**Whyspec:** MAJOR.MINOR` placed as [REC-139] places `**Id:**`. The label is matched
case-insensitively, and only the first such line outside a fenced block ([REC-158]) counts. A
parser **MUST** yield the value as `format_version` when present and **MUST** leave it absent when
not: absence means the record does not state its version ([VER-005]), and the current
interpretation applies to it, which is what each migration note exists to define. A parser
**MUST NOT** reject a record whose marker names a version it does not know; it **MUST** read the
record under the newest version it implements and yield the marker as written. A consumer **MAY**
treat a marker newer than it knows as a signal about the record; the parser may not. A marker that
does not match `\d+\.\d+` **MUST** be yielded absent, as [REC-129] treats a malformed date.

> The marker is optional because the population that needs it is small: a record is pinned only
> when its author wants an older meaning kept after a meaning change, and most records are read
> under whatever the document currently says. The migration note carries the weight instead — it is
> the one paragraph an implementer reads to learn what changed for the records already in the
> world — and [VER-010] makes writing it a condition of merging rather than a courtesy. The label is
> the specification's own name rather than `Format` or `Spec` because a record's prose uses those
> words for other things, and an inline field is matched by its label. Forward tolerance follows
> [ENV-008]'s reasoning in reverse: an unknown status is a failure because it hides a refusal, but an
> unknown version marker hides nothing — the record is still a record, and refusing it would delete
> it from a corpus for having been written by a newer tool.

## 8. Open questions

Places where this document deliberately does not yet state a rule. Each is recorded rather than
filled, because an invented rule is worse than an acknowledged question: implementers build on it,
and it becomes real without ever having been decided.

| Id | Question |
|---|---|
| **Q2** | **Section heading level.** `### Decision` and `###### Decision` are both accepted (§4.5). Whether parsers should tighten to level 2, or only emitters be constrained ([REC-020]), is undecided. |
| **Q7** | **Which node fields each envelope variant projects.** No stated principle governs it; a field added to the node in one section does not automatically reach the variant that enumerates the output. |
| **Q8** | **Multiple `## Decision` sections are first-wins with no diagnostic** ([REC-019]). Whether a second Decision section should be an error is undecided. |
| **Q9** | **A record whose title is duplicated within one directory.** Identity ([REC-071]) includes the source path, so two records with the same title in different files are distinct nodes; two in the *same* file are not addressable separately. |
| **Q10** | **The `attested` tier has no record syntax.** It is normatively ordered ([PROV-002]) but is produced from sources outside this format's scope (§1.4). An implementation that only reads records will never mint it. |
| **Q12** | **Empty `## Recommendation`.** [REC-046] says an empty recommendation yields no delta, but an emitter is not forbidden from writing an empty section, and a parser cannot distinguish "recommended nothing" from "written and left blank". |

Questions resolved by a rule are recorded in [CHANGELOG.md](../CHANGELOG.md), not here.

---

## 9. Conformance

A conforming implementation satisfies every **MUST** and **MUST NOT** in §§3–7 **that constrains an
implementation**, for the surfaces it implements. An implementation that only reads records need not
implement §6; an implementation that only answers queries need not implement §4.10 or §4.11.

Rules in **Appendix A** are **reserved**: retained with their fixtures for an implementation that
adopts a variant, and outside the conformance obligation until one does.

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

Conformance is demonstrated against the **Whyspec conformance corpus** — a set of fixture records
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
| REC-001 | The bare, extensionless filename Whyfile at a repository root is RESERVED by this specification and is explicitly unclaimed. |
| REC-002 | A record MUST be a UTF-8 encoded markdown document. |
| REC-003 | A parser MUST tolerate a leading UTF-8 byte-order mark (U+FEFF) and MUST NOT let its presence change the parse. |
| REC-004 | A parser MUST treat a line matching ^(#{1,6})\s+(.+)$ as a heading, where the count of # characters is the heading level and the remainder, trimmed…. |
| REC-005 | Heading text MUST be matched case-insensitively when a parser is deciding which section a heading names. |
| REC-006 | YAML front matter, if present, MAY be interpreted, but only as a lower-precedence source that can never override the markdown body, and only for the…. |
| REC-007 | A parser MUST NOT require any section not named in §4. Unrecognized sections MUST be ignored without error. |
| REC-008 | A markdown document is a record if and only if both of the following hold: — see the rule body for the enumeration. |
| REC-009 | The record kind is determined by which level-1 form matched: — see the rule body for the enumeration. |
| REC-010 | A parser MUST use the first level-1 heading that matches any declared form as the record's title heading, and MUST ignore any later level-1 heading. |
| REC-011 | An ADR heading MUST match, case-insensitively: — see the rule body for the enumeration. |
| REC-012 | The separator is REQUIRED. |
| REC-013 | The digit run MUST NOT be required to be zero-padded or of any fixed width for *heading recognition*. # ADR-7: Title is a valid ADR heading. |
| REC-014 | A decision heading MUST match, case-insensitively: — see the rule body for the enumeration. |
| REC-015 | The record's title is the matched heading text with its prefix (the ADR-… run and separator, or the Decision: literal) removed, and surrounding…. |
| REC-016 | The title MUST be non-empty. A record whose title reduces to the empty string MUST NOT be treated as a record. |
| REC-017 | For a decision record the title is, by construction, the chosen option. |
| REC-018 | A parser MUST recognize the following section headings, matched case-insensitively against the full trimmed heading text: — see the rule body for the enumeration. |
| REC-019 | When more than one section matches the Decision heading, the parser MUST use the first and ignore the rest. |
| REC-020 | Records SHOULD write all sections in REC-018 at heading level 2. |
| REC-021 | The Context section carries the question the record answers. Emitters MUST render it (§4.10). |
| REC-022 | The alternatives section body MUST be parsed as a flat list. |
| REC-023 | Each item's text MUST be normalized by collapsing all whitespace runs to a single space, trimming, and removing every  sequence. |
| REC-024 | Alternatives MUST be yielded in document order. |
| REC-025 | A prose (list-free) alternatives section MUST yield an empty alternatives list, not an error and not the prose. |
| REC-026 | Records SHOULD NOT nest list items under an alternative. |
| REC-027 | A record's status MAY be given in either of two forms: — see the rule body for the enumeration. |
| REC-028 | When both forms are present the inline form MUST win. |
| REC-029 | The inline form MUST be searched over the whole document, and the first line-anchored match MUST win. It is not scoped to any section. |
| REC-030 | A status value MUST be normalized by lowercasing it and then taking its first run of alphabetic characters. |
| REC-031 | When no status can be determined, the parsed record's status MUST be absent. |
| REC-032 | A record whose normalized status is rejected MUST NOT become ground-truth intent of any tier, and its assumptions MUST NOT either. |
| REC-033 | The status values carrying normative behaviour are exactly those classified in §4.6.1 — draft, proposed, accepted, rejected — together with the…. |
| REC-034 | Each list item in the Assumptions section (parsed per REC-022–REC-025) MUST yield one assumption with a claim, plus two optional fields. |
| REC-035 | An item MAY carry a review date matching, case-insensitively, \(?\s*review -by:?\s*(\d{4}-\d{2}-\d{2})\s*\)? — accepting (review by 2027-01-31) and…. |
| REC-036 | review_by MUST be a full ISO-8601 calendar date, YYYY-MM-DD. |
| REC-037 | An item MAY carry an expiry condition matching, case-insensitively, \(\s*expires?:?\s*(^)+?)\s*\). |
| REC-038 | After both strippings, the claim MUST be normalized by collapsing whitespace and trimming spaces and periods from both ends. |
| REC-039 | review_by and expiry MUST be omitted entirely when not present, not serialized as null. |
| REC-040 | A record declares supersession in prose. A parser MUST collect every match of \bsupersedes?\s+(ADR-\d+), case-insensitively, over the whole document. |
| REC-041 | The passive form — "superseded by ADR-N" — MUST NOT be read as a supersession claim. |
| REC-042 | Collected references MUST be uppercased, de-duplicated, and yielded in first-seen order. |
| REC-043 | Resolving a reference to a target record MUST be done by the ADR number in the target's filename, taken as the first run of exactly four digits. |
| REC-044 | A supersession reference that resolves to no known record MUST be dropped silently, not reported as a violation. |
| REC-045 | When a record carries a Recommendation section whose trimmed body differs from the record's trimmed title, the resulting intent node MUST carry a…. |
| REC-046 | When the recommendation is absent, empty, or equal to the title, resolution_delta MUST be omitted from the node entirely. |
| REC-047 | The Status: and Date: lines MUST be emitted on adjacent lines immediately after a single blank line following the H1, with no blank line between them. |
| REC-048 | Section order MUST be: Context, Decision, Alternatives considered, then Recommendation. |
| REC-049 | The Recommendation section MUST be emitted only when a non-empty recommendation was supplied, and MUST be omitted entirely otherwise. |
| REC-050 | When no question was supplied, the Context body MUST be the literal (none recorded). |
| REC-051 | When the rationale is empty, the Decision body MUST be the chosen option (the title). |
| REC-052 | Alternatives MUST be emitted as a flat, one-based, N. numbered list in the order supplied. |
| REC-053 | The document MUST end with a single trailing newline. |
| REC-054 | A (none recorded) placeholder MUST be emitted only for a section where the absence of content is itself an answer — "we considered the question and…. |
| REC-056 | A record's filename SHOULD be YYYY-MM-DD-<question-slug>.md, where the date is the UTC calendar date of capture and the slug derives from the…. |
| REC-057 | Records SHOULD live under docs/decisions/; ADR records SHOULD live under docs/adr/. |
| REC-058 | A slug MUST be derived from its source text by: — see the rule body for the enumeration. |
| REC-059 | A slug MUST be bounded at 60 characters. |
| REC-060 | Truncation MUST land on a word boundary: truncate to the bound, then, if the result contains a -, drop everything from the last - onward, then strip…. |
| REC-061 | If the first word alone exceeds the bound, the slug MUST be hard-cut. A slug must be bounded; this is the only case where a mid-word cut is permitted. |
| REC-062 | A slug that reduces to the empty string MUST become the literal decision. |
| REC-064 | Legacy name. |
| REC-065 | A legacy file MUST NOT be claimed on filename alone. |
| REC-066 | A question that is empty MUST be treated as matching a recorded context of (none recorded), and only that. |
| REC-067 | Existing dated record. |
| REC-068 | The date portion of the pattern in REC-067 MUST be expressed with digit character classes. Neither *-<slug>.md nor ????-??-??-<slug>.md is acceptable. |
| REC-069 | Fresh name. |
| REC-070 | A record's filename MUST NOT be changed by an implementation once written. _(out of scope: action)_ |
| REC-071 | An intent node's identity MUST be derived from exactly four inputs, joined by :: in this order, and hashed: — see the rule body for the enumeration. |
| REC-072 | The normalized label MUST be the label lowercased, with every run of characters outside a-z0-9 replaced by _, and leading/trailing _ stripped. |
| REC-073 | The canonical source path MUST be the repository-relative path in POSIX separator form. |
| REC-074 | A path outside any repository MUST fall back to a POSIX-normalized absolute spelling. Path canonicalization MUST NOT raise. |
| REC-075 | A record MAY carry an identifier in the inline field form, Id: <value>, placed with Status and Date. |
| REC-076 | An identifier, once written, MUST NOT be regenerated, and MUST NOT be derived from any mutable part of the record. |
| REC-078 | An identifier MUST be unique within a corpus. Two records sharing an identifier is an error; neither MUST be treated as the referent. |
| REC-079 | A record MAY carry an ## Attribution section, one attribution per list item, in the form <role> <kind>:<id> on <date>. |
| REC-080 | <kind> MUST be one of exactly human or agent. <role> MUST be one of exactly drafted, decided, or ratified. |
| REC-081 | A record MAY carry any number of attributions, including several sharing a role. An absent attribution MUST be read as *unrecorded*. |
| REC-082 | A record MAY carry a ## Governs section listing the artifacts the decision governs, one per list item. |
| REC-083 | Each item MUST be an artifact reference. |
| REC-084 | An absent ## Governs section MUST be read as *scope not declared*. It MUST NOT be read as *governs nothing*. |
| REC-086 | An artifact reference that resolves to zero artifacts MUST be reported as a distinct, named state — neither silently dropped nor treated as an error. |
| REC-087 | A record MAY carry a ## Relations section, one relation per list item, in the form <relation> <identifier>. |
| REC-088 | <relation> MUST be one of exactly supersedes, refines, constrains, motivated_by, trade_off_against, or contradicts. |
| REC-089 | <identifier> MUST be a record identifier (REC-075) or an ADR number. |
| REC-090 | A relation whose target cannot be resolved MUST be dropped silently, per the same reasoning as REC-044 — a corpus may be partial. |
| REC-091 | A relation whose target is ambiguous — resolving to more than one candidate record — MUST be dropped, and MUST NOT be resolved to any one of them. |
| REC-093 | A record MAY carry an ## Evidence section, one entry per list item, in the form <method>: <qualifier>, where the qualifier is optional. |
| REC-094 | <method> MUST be one of exactly grep, diff, executed, read, or traced. |
| REC-095 | An entry MAY cite the deliberation that produced the decision, as a reference to where that deliberation occurred. A citation MUST be a reference. |
| REC-096 | A record with no ## Evidence section records nothing about method. It MUST NOT be read as *no evidence existed*, and MUST NOT be flagged on that basis. |
| REC-097 | An alternative item MAY carry a disposition and a rejection rationale, in the form <option> — <disposition>: <rationale>. |
| REC-098 | <disposition> MUST be one of exactly rejected, deferred, partially-adopted, or not-evaluated. |
| REC-099 | An alternative carrying no disposition MUST yield the whole item as its option text, with disposition and rationale absent. |
| REC-100 | deferred MUST NOT be treated as equivalent to rejected. A deferred option remains available. |
| REC-101 | A record's normalized status (REC-030) MUST determine every one of the following, by lookup in this table and by no other means. |
| REC-104 | A record whose disposition is declined MUST yield foreclosure intent: it MUST be retained and queryable, MUST NOT be counted toward any…. |
| REC-105 | A supersession reference that resolves to more than one candidate record MUST be dropped, exactly as REC-044 drops an unresolved one. |
| REC-106 | A filename MUST NOT be treated as carrying an ADR number when the four-digit run is part of a date. |
| REC-107 | A parser MUST yield the Context body as a question field on the parsed record, and it MUST reach the intent node. |
| REC-108 | superseded MUST NOT be a status. A record is superseded when, and only when, another record declares a supersedes relation naming it (§4.16). |
| REC-110 | A review surface SHOULD NOT present a draft record, and SHOULD present a proposed one. Both remain queryable on request. |
| REC-111 | A record's currency — whether the decision it carries is still live — MUST be derived from the relation graph. It MUST NOT be authored on the record. |
| REC-112 | Where REC-101's Currency defined column is *yes*, a record is historical when at least one other record declares a supersedes relation naming it, and…. |
| REC-113 | Supersession MUST be applied transitively. Where A supersedes B and B supersedes C, both B and C are historical. |
| REC-114 | A record participating in a supersession cycle MUST be reported as having indeterminate currency. |
| REC-115 | The roles are distinct and MUST NOT be conflated. |
| REC-116 | Where a record carries an ## Attribution section, ratification governs its provenance tier and the kind-based assignment of PROV-005/PROV-006 MUST…. |
| REC-117 | Each attribution MUST carry its own provenance (§5.5) and MAY carry a date. Where a date is present it MUST be a full ISO-8601 calendar date. |
| REC-118 | A ratification is self-ratification when the same actor also carries the role drafted or decided on that record. |
| REC-119 | A ratification alone MUST NOT promote a record to authored. |
| REC-120 | A self-ratification and an uncorroborated ratification MUST NOT be discarded. |
| REC-121 | The four inputs MUST be joined by exactly :: with no surrounding whitespace. |
| REC-122 | The intent kind component is the kind of the node, and MUST be exactly decision or assumption. |
| REC-123 | The identity MUST be intent_ followed by the first 12 characters of the lowercase hexadecimal SHA-1 digest of the joined string encoded as UTF-8. |
| REC-124 | Only the label component is normalized (REC-072). |
| REC-127 | For an assumption node, the source location and the normalized label are both derived from the claim as REC-038 yields it — the claim after the…. |
| REC-128 | An actor is the ordered pair (kind, id) taken from an attribution's <kind>:<id> term. |
| REC-129 | An attribution whose date is present but is not a full ISO-8601 calendar date (REC-117) MUST be yielded with its date absent. |
| REC-130 | A parser reading a record whose ## Evidence entry names a method outside REC-094's set MUST drop that entry and MUST NOT yield the value as a method. |
| REC-131 | A directory ingest MUST consider exactly those entries in the directory whose name ends in .md and does not begin with . |
| REC-132 | Where a document's first line is exactly ---, the bytes from that line through the next line that is exactly ---, inclusive, are YAML front matter…. |
| REC-133 | In REC-097's form the separator is exactly one of em dash — (U+2014), en dash – (U+2013), or hyphen-minus -, with at least one whitespace character…. |
| REC-134 | The alternatives a parser yields are objects, each carrying option and, where recorded, disposition and rationale (REC-097–REC-099). |
| REC-135 | Emitter completeness. An emitter MUST be able to render every field a parser yields (§4.5–§4.17). |
| REC-136 | Status provenance. The value rendered on the Status: line MUST be the record's own status. |
| REC-137 | Where a record carries the corresponding field, an emitter MUST render each of these sections, in this order, after ## Decision and before ##…. |
| REC-138 | An emitter MUST omit any of these sections entirely when its field is absent or empty, and MUST NOT emit a placeholder for it (REC-054). |
| REC-139 | An emitter MUST render the Id: line, adjacent to Status: and Date:, when the record carries an identifier. |
| REC-140 | A Decision section whose body is empty MUST yield rationale as an empty string, not an absent key. |
| REC-141 | The properties REC-101 determines MUST be carried on the parsed record and the intent node under these key spellings: deliberation, offered, and…. |
| REC-142 | A numbered heading MUST match <one or more digits>. <title> — digits, a full stop, whitespace, then a non-empty title. |
| REC-143 | A level-1 heading of any other shape MUST be accepted as a record heading if and only if the document carries an ADR section signature, which is…. |
| REC-144 | The signature MUST NOT be weakened to a subset. |
| REC-145 | A parser MUST accept the following alternative spellings as the sections named, and MUST treat them as carrying the same obligation: — see the rule body for the enumeration. |
| REC-146 | A section heading MAY carry a trailing HTML comment, and a parser MUST ignore it when matching the heading. |
| REC-147 | Status MAY additionally be written as a list item, - Status: <value>, and a parser MUST read it where no inline Status: field is present. |
| REC-148 | A record whose title is a placeholder MUST NOT be treated as a record. A title is a placeholder when any of the following hold: — see the rule body for the enumeration. |
| REC-149 | The only front-matter key a parser MAY interpret is title, and it MUST be used only where the document has no level-1 heading at all. |
| REC-150 | status MUST NOT be read from front matter, even where the body states no status. |
| REC-151 | A symbol reference MUST be written <path>#<symbol> — a repository-relative path carrying no glob metacharacter, a single #, and a non-empty symbol…. |
| REC-152 | A path glob item MUST be read as exactly one of three forms, decided by its text after REC-153's normalization: — see the rule body for the enumeration. |
| REC-153 | Before classification under REC-152 and REC-151, a reader MUST derive the reference from the item text REC-082 yields, in this order: — see the rule body for the enumeration. |
| REC-154 | An artifact reference is repository-relative. A writer MUST NOT begin an item with /. |
| REC-155 | An implementation that resolves scope at file granularity MAY resolve a symbol reference (REC-151) to the file it names, by the path before its #. |
| REC-156 | REC-152–REC-155 govern declared scope items. |
| REC-157 | A Governs alias MUST count as the record's declared scope only where its body yields at least one item under REC-082. Where an alias body yields no…. |
| REC-158 | A fenced code block — the lines from one whose trimmed text begins with three backticks or three tildes, through the next line whose trimmed text…. |
| REC-159 | A record MAY carry its date in the inline field form, Date: <value>. |
| REC-160 | A list item whose text begins with the inline field — - Status: <value> — is the list-item form of REC-147 wearing both markers, and a parser MUST…. |
| REC-161 | Status MAY also be written bare — a line that begins Status: after any leading whitespace, case-insensitively, with no emphasis and no list marker —…. |
| REC-162 | Where the operative section selected under REC-018, REC-019 and REC-145 — Decision, or failing that one of its aliases — has an empty body (REC-004)…. |
| REC-163 | Where a record has an operative section, every level-2 section whose heading's first word is Why, matched case-insensitively — ## Why, ## Why not a…. |

#### Provenance

| Id | Statement |
|---|---|
| PROV-001 | Provenance MUST be one of exactly five values. The set is closed; an implementation MUST NOT mint a sixth without a version marker (§7, VER-003). |
| PROV-002 | The tiers MUST be totally ordered, highest trust first: — see the rule body for the enumeration. |
| PROV-003 | Intent with absent or unrecognized provenance MUST be ranked as reconstructed. |
| PROV-004 | When results are ordered by trust, provenance MUST be the primary sort key and any numeric confidence the secondary key. |
| PROV-005 | An ADR record (REC-009) carrying no ## Attribution section MUST yield authored intent. |
| PROV-006 | A decision record (REC-009) carrying no ## Attribution section MUST yield captured intent. |
| PROV-007 | An assumption node SHOULD inherit the provenance tier of the record that declared it. |
| PROV-008 | Intent ingested from a record MUST carry a numeric confidence of 1.0. The record *is* the evidence; there is nothing to be uncertain about at ingest. |
| PROV-009 | An implementation MUST NOT conflate provenance with a numeric confidence score or with any string confidence label from an extraction pipeline. |
| PROV-010 | The golden tiers — the evidence classes that count as trusted — MUST be exactly {authored, captured, attested, reconstructed-then-ratified}. |
| PROV-012 | A trust metric MUST NOT blend tiers into a single scalar without also reporting the per-tier breakdown. |
| PROV-013 | An edge — any relationship between two intent nodes, or between an intent node and an artifact, including every declared or inferred scope binding…. |
| PROV-015 | A binding between intent and an artifact MUST be reconstructed unless it was declared (§4.15). |
| PROV-016 | Ordering and trust rules (PROV-002, PROV-004) apply to edges exactly as they apply to nodes. |
| PROV-017 | Disposition (§4.6.1) and provenance MUST be treated as independent axes. |
| PROV-018 | Foreclosure intent MUST NOT be counted toward any trusted-evidence metric (PROV-010), regardless of its provenance tier. |
| PROV-019 | A result containing intent MUST expose disposition, so a consumer can partition commitments from foreclosures without inspecting record text. |
| PROV-020 | A consumer MUST NOT present foreclosure intent as an answer to what the authoring team *does*. |
| PROV-021 | Where a record carries an ## Attribution section and at least one drafted or decided actor is human, its tier MUST be determined by ratification…. |
| PROV-022 | Where a record carries an ## Attribution section naming at least one drafted or decided actor and every such actor is agent, the record is…. |

#### Envelope

| Id | Statement |
|---|---|
| ENV-001 | A query result MUST be a single JSON object. Not an array, not a stream of objects, not a bare value. _(reserved: Appendix A)_ |
| ENV-002 | Every envelope MUST carry a command key: a stable lowercase string naming the operation that produced it. _(reserved: Appendix A)_ |
| ENV-003 | Every envelope MUST carry a status key: a lowercase snake_case token classifying the outcome. _(reserved: Appendix A)_ |
| ENV-004 | command and status are the only universal keys. A consumer MUST NOT assume any other key is present without first dispatching on command. _(reserved: Appendix A)_ |
| ENV-005 | The envelope MUST be modelled as a tagged union discriminated by command, over a small universal core of {command, status}. _(reserved: Appendix A)_ |
| ENV-006 | Where a single command value carries more than one disjoint shape, the spec MUST name the secondary discriminator explicitly, and a consumer MUST…. _(reserved: Appendix A)_ |
| ENV-007 | Status tokens are per-command, not global. The following are the defined tokens. _(reserved: Appendix A)_ |
| ENV-008 | A consumer encountering an unrecognized status token MUST treat it as a failure. _(out of scope: consumer)_ |
| ENV-009 | A status MUST NOT be overloaded to carry data. _(out of scope: consumer)_ |
| ENV-010 | A status that reports an honest negative — no_changes, no_strong_match, no_intent_governing_changes, no_references — is a complete answer, not an…. _(reserved: Appendix A)_ |
| ENV-011 | An envelope reporting a failure MUST carry command, status, and a human- readable message. It MUST NOT be required to carry any variant-specific key. _(reserved: Appendix A)_ |
| ENV-013 | The why envelope MUST carry: query (the question as asked), count (number of results returned), cutoff (the strong-match score threshold in effect)…. _(reserved: Appendix A)_ |
| ENV-014 | score_stats MUST be an object with top, runner_up, and median — computed over the whole scored field, not only the returned rows. _(reserved: Appendix A)_ |
| ENV-015 | Each entry in results MUST carry: disposition, score, id, label, intent_kind, claim, rationale, alternatives, source_file, source_location…. _(reserved: Appendix A)_ |
| ENV-016 | alternatives MUST be a list of strings. _(reserved: Appendix A)_ |
| ENV-017 | The three evidence fields have fixed meanings, and an implementation MUST NOT redefine them: — see the rule body for the enumeration. _(reserved: Appendix A)_ |
| ENV-018 | matched_coverage MUST be in 0, 1 inclusive. _(reserved: Appendix A)_ |
| ENV-019 | The topically_weak status MUST mean: the top result cleared the score cutoff, but its match evidence does not support treating it as an answer. _(reserved: Appendix A)_ |
| ENV-020 | The weak_match status MUST mean: the top result scored *under* the cutoff but stands clearly apart from the runner-up — a probable answer at moderate…. _(reserved: Appendix A)_ |
| ENV-021 | The list-intent envelope MUST carry count, filter, and intent. _(reserved: Appendix A)_ |
| ENV-022 | Each entry in intent MUST carry: id, label, intent_kind, claim, rationale, source_file, source_location, confidence_score, provenance, disposition. _(reserved: Appendix A)_ |
| ENV-023 | The ok variant MUST carry query, resolved, intent, explains, and relations. _(reserved: Appendix A)_ |
| ENV-024 | The ambiguous variant MUST carry candidates and message and MUST NOT carry resolved. _(reserved: Appendix A)_ |
| ENV-025 | The changed envelope MUST carry base (the reference diffed against, or null when files were supplied explicitly), changed_files, files_with_intent…. _(reserved: Appendix A)_ |
| ENV-026 | ambiguous on a result MUST be true when the file was matched by basename and that basename resolves to more than one path. _(reserved: Appendix A)_ |
| ENV-027 | The digest envelope MUST carry since, added, removed, and superseded. _(reserved: Appendix A)_ |
| ENV-029 | A component of intent_debt that the implementation cannot compute MUST be reported as explicit null, never as 0. A zero claims "we measured and found…. _(reserved: Appendix A)_ |
| ENV-030 | The check envelope MUST carry rules (count of rules evaluated), files_checked, and violations. _(reserved: Appendix A)_ |
| ENV-032 | A rule of a type the checker does not implement MUST be skipped — never counted as a pass and never counted as a failure. _(reserved: Appendix A)_ |
| ENV-033 | Both MUST distinguish *governed by a decision* from *governed by a constraint*. _(reserved: Appendix A)_ |
| ENV-034 | The capture envelope MUST carry record (the path as given, from which node identity derives), record_abs (the resolved absolute destination)…. _(reserved: Appendix A)_ |
| ENV-036 | merged MUST report whether any secondary view the implementation maintains was updated, independently of status. _(reserved: Appendix A)_ |
| ENV-037 | resolution_delta MUST be present with an explicit null when there was no delta. _(reserved: Appendix A)_ |
| ENV-038 | A key omitted from a JSON object this specification defines — a node, a reserved envelope (Appendix A), or an intent-layer object MUST mean *not…. _(out of scope: consumer)_ |
| ENV-039 | An implementation MUST NOT use the two interchangeably. _(out of scope: consumer)_ |
| ENV-044 | The summary coverage variant MUST carry exactly these twelve coverage-specific keys alongside command and status: code_files, code_symbols…. _(reserved: Appendix A)_ |
| ENV-045 | intent_debt MUST carry exactly these four components: dark_files, orphaned_intent, stale_decisions, unresolved_disputes. _(reserved: Appendix A)_ |
| ENV-047 | The envelope field intent_kind names the kind of the node and is not constrained to REC-122's pair. _(reserved: Appendix A)_ |
| ENV-048 | Each entry in a check envelope's violations MUST carry rule, file, message, and decision_id. _(reserved: Appendix A)_ |
| ENV-049 | The summary coverage variant's top-level dark_files MUST be an array of repository-relative paths, and MUST NOT be a count. _(reserved: Appendix A)_ |
| ENV-050 | The golden block MUST carry exactly these five components: golden_tiers (the array of tier names counted as trusted, per PROV-010), by_provenance (an…. _(reserved: Appendix A)_ |
| ENV-051 | A recall envelope MUST consist of a preamble followed by one section per record delivered, in that order. |
| ENV-052 | The preamble MUST state four things, in any wording: that recorded decisions govern the named path; that their author is not present in the session…. |
| ENV-053 | Each record section MUST begin with a level-2 heading carrying, in order, the record's title; its status, or the words status not stated; its date…. |
| ENV-054 | The decision text in a section MAY be bounded, and the bound is implementation-defined. |
| ENV-055 | In the plan-gate form, the sections MUST be preceded by a header naming the count of records delivered. |

#### Versioning

| Id | Statement |
|---|---|
| VER-001 | A version marker and a migration note are REQUIRED exactly when a change alters how an EXISTING field or section is interpreted — a *meaning change*. _(out of scope: governance)_ |
| VER-002 | A change that adds a new optional field or section — a *vocabulary extension* — MUST NOT require a version marker. _(out of scope: governance)_ |
| VER-003 | Each of the following is a meaning change and MUST carry a version marker and a migration note: — see the rule body for the enumeration. _(out of scope: governance)_ |
| VER-004 | Each of the following is a vocabulary extension and MUST NOT carry a version marker: — see the rule body for the enumeration. _(out of scope: governance)_ |
| VER-005 | A change MUST NOT re-interpret the absence of a field in existing records as a claim or retroactively infer a value the record does not carry. _(out of scope: governance)_ |
| VER-007 | The version marker governs the record format and the core envelope only. _(out of scope: governance)_ |
| VER-008 | This document defines the pre-publication baseline, and the record format carries no explicit version marker in that baseline. _(out of scope: governance)_ |
| VER-009 | The specification carries a version of the form MAJOR.MINOR, stated in its header. A meaning change (VER-001, VER-003) MUST increment MINOR. _(out of scope: governance)_ |
| VER-010 | Every meaning change MUST add one row to the migration table below before it merges: the new version, the rule ids whose meaning changed, and a…. _(out of scope: governance)_ |
| VER-011 | A record MAY declare the format version it was written to, as an inline field Whyspec: MAJOR.MINOR placed as REC-139 places Id: — see the rule body for the enumeration. |

---

---

## Appendix A. Reserved command variants

The envelopes in this appendix were specified for an earlier implementation and are not emitted by
the maintainer's. Each is **reserved**: its rules keep their identifiers and text, its fixtures are
retained, and neither counts toward conformance (§9). A reserved variant anticipates a capability
named beside it; an implementation that builds that capability may adopt the variant as specified
or propose a change to it under §7.

| Variant | Anticipates |
|---|---|
| `why` | free-text retrieval over recorded intent; the recall envelope (§6) is its successor for delivery at a coupling point |
| `list-intent` | the plan-gate recall at the intention coupling point |
| `explain` | in-flight recall of one decision by identifier |
| `changed` | the mechanical validity check of a change against the records that govern it |
| `digest` | onboarding and seeding of a ledger from history |
| `coverage` | governance coverage measurement as a product metric |
| `check` | the mechanical validity check; the maintainer's checker has a different shape, and if it is ever published it enters the intent-layer profile as an optional object |
| `intent-diff` | the supersession entries of the attestation record ([INT-007]) |
| `review-context` | the land coupling point: a pull-request gate |
| `capture` | writing a record at the moment of choosing; the capture skill writes a file and emits no envelope |


### A.1 Shape

**[ENV-001]** A query result **MUST** be a single JSON object. Not an array, not a stream of
objects, not a bare value.

**[ENV-002]** Every envelope **MUST** carry a `command` key: a stable lowercase string naming the
operation that produced it.

**[ENV-003]** Every envelope **MUST** carry a `status` key: a lowercase `snake_case` token
classifying the outcome.

**[ENV-004]** `command` and `status` are the **only** universal keys. A consumer **MUST NOT** assume
any other key is present without first dispatching on `command`.

This is the single most important rule in this appendix, and it is easy to get wrong by inspection of one
command.

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

### A.2 The envelope is a tagged union

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

> `coverage` overloading one `command` tag with two payloads is the weakest point in the union. A
> future revision may give the explanation form its own tag; that is a meaning change under
> [VER-001] and needs its own migration row.

### A.3 Status

**[ENV-007]** Status tokens are **per-command**, not global. The following are the defined tokens.

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

### A.4 The error variant

**[ENV-011]** An envelope reporting a failure **MUST** carry `command`, `status`, and a human-
readable `message`. It **MUST NOT** be required to carry any variant-specific key.
A consumer **MUST NOT** assume a variant-specific key is present merely because `command` names a
variant that normally has it; the error variant is a legitimate shape with none of those keys.

### A.5 Command variants

Field lists below are normative for the variant they name.

#### A.5.1 `why`

Free-text retrieval over recorded intent.

**[ENV-013]** The `why` envelope **MUST** carry: `query` (the question as asked), `count` (number of
results returned), `cutoff` (the strong-match score threshold in effect), `score_stats`, and
`results`.

**[ENV-014]** `score_stats` **MUST** be an object with `top`, `runner_up`, and `median` — computed
over the **whole scored field**, not only the returned rows. This is what makes "a lone hit standing
above a flat tail" machine-detectable by the consumer rather than a judgement only the implementation
can make.

**[ENV-015]** Each entry in `results` **MUST** carry: `disposition`, `score`, `id`, `label`, `intent_kind`,
`claim`, `rationale`, `alternatives`, `source_file`, `source_location`, `provenance`,
`matched_terms`, `distinctive_matches`, `matched_coverage`.

**[ENV-016]** `alternatives` **MUST** be a list of strings. An implementation reading a legacy scalar
**MUST** coerce it to a single-element list, and **MUST NOT** iterate a bare string character by
character.

**[ENV-047]** The envelope field `intent_kind` names the kind of the node and is **not** constrained
to [REC-122]'s pair. [REC-122] governs the third component of node identity ([REC-071]) for a node
derived from a record, where the only kinds are `decision` and `assumption`. An implementation
**MUST NOT** hash any other value as that component, and **MUST NOT** reject an envelope carrying
another value in this field. This rule governs the field wherever it appears, not only on a `why`
result.

> The field carries the same name in both places and means two things. [ENV-033] requires
> `intent-diff` and `review-context` to distinguish *governed by a decision* from *governed by a
> **constraint***, so the envelope field must admit kinds such as `constraint`, `mechanism` and
> `tradeoff`; §1.4 puts intent derived from non-record sources out of scope, which is exactly where
> those kinds come from.

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

#### A.5.2 `list-intent`

**[ENV-021]** The `list-intent` envelope **MUST** carry `count`, `filter`, and `intent`. `filter`
**MUST** echo the filter that was applied, with an explicit `null` for each unset criterion — a
consumer must be able to see what was *not* filtered.

**[ENV-022]** Each entry in `intent` **MUST** carry: `id`, `label`, `intent_kind`, `claim`,
`rationale`, `source_file`, `source_location`, `confidence_score`, `provenance`, `disposition`.

> `disposition` is in this list because [PROV-019] requires a result carrying intent to expose it,
> and [ENV-004] tells consumers not to assume any key the list does not name; a requirement stated
> elsewhere has to reach the list that enumerates the output.

#### A.5.3 `explain`

**[ENV-023]** The `ok` variant **MUST** carry `query`, `resolved`, `intent`, `explains`, and
`relations`. `resolved` **MUST** report how the argument was matched (`matched_by`) and, for a
non-exact match, a `score`.

**[ENV-024]** The `ambiguous` variant **MUST** carry `candidates` and `message` and **MUST NOT**
carry `resolved`. Ambiguity is not a partial answer; an implementation **MUST NOT** silently pick a
candidate.

#### A.5.4 `changed`

**[ENV-025]** The `changed` envelope **MUST** carry `base` (the reference diffed against, or null
when files were supplied explicitly), `changed_files`, `files_with_intent`, and `results`. Each
result **MUST** carry `file`, `matched_by`, `ambiguous`, and `governed_by`.

**[ENV-026]** `ambiguous` on a result **MUST** be true when the file was matched by basename and
that basename resolves to more than one path. A basename match that could mean several files
**MUST** be reported as such rather than silently resolved.

#### A.5.5 `digest`

**[ENV-027]** The `digest` envelope **MUST** carry `since`, `added`, `removed`, and `superseded`.

#### A.5.6 `coverage`

**[ENV-044]** The summary `coverage` variant **MUST** carry exactly these twelve coverage-specific
keys alongside `command` and `status`: `code_files`, `code_symbols`, `files_with_intent`,
`symbols_with_intent`, `authored_anchored_files`, `authored_anchored_symbols`, `file_coverage_pct`,
`symbol_coverage_pct`, `dark_files`, `intent_by_kind`, `golden`, `intent_debt`.

**[ENV-050]** The `golden` block **MUST** carry exactly these five components:
`golden_tiers` (the array of tier names counted as trusted, per [PROV-010]), `by_provenance` (an
object mapping every tier to its integer count), `golden_count` (the integer total across the
golden tiers), `total_intent` (the integer total across all tiers), and `golden_fraction_pct`
(the integer percentage). A trust metric **MUST NOT** report `golden_fraction_pct` without the
`by_provenance` breakdown, per [PROV-012].

> Naming the components is what stops the next author guessing: a block with a required count and
> no named parts invites two incompatible shapes, each individually plausible. The marker was correct that the
> gap was real; what it could not do was prevent anyone walking into it.

**[ENV-049]** The summary `coverage` variant's top-level `dark_files` **MUST** be an **array of
repository-relative paths**, and **MUST NOT** be a count. The `dark_files` inside `intent_debt`
([ENV-045]) remains an **integer** count. An implementation **MUST NOT** use the same shape for
both.

> The two keys share a name and answer different questions — *which files* against *how many* —
> and leaving the outer one untyped let a corpus carry both readings under one name, in fixtures
> that were each individually labelled valid. That is the confusion [ENV-009] warns about, one
> level down: a consumer reading `dark_files` had no way to know whether it would receive a length
> or a list.
>
> The array is the right shape for the outer key precisely *because* the count already exists
> inside `intent_debt`. Typing it as a count would make the envelope carry the same number twice
> and lose the paths entirely; typing it as an array makes the pair complementary, and a consumer
> wanting the number can take the length.

> §6.1 has always stated the count and never the names. A
> required count that no rule lets a validator satisfy is not a requirement; it is a number. The
> names are those the conformance corpus instantiates.
>
> **Open: the type of `dark_files` at this level.** Two corpus fixtures both labelled valid once
> disagreed — one carrying a list of paths, the other an integer count — which is the [ENV-009]
> defect one level down, the same name meaning *how many* in one file and *which ones* in the other.
> This rule names the key and does not settle the type. [ENV-045] already puts a `dark_files`
> **count** inside `intent_debt`, so the list reading is the one that adds information here rather
> than duplicating it, and it is the reading every valid fixture now takes.

**[ENV-029]** A component of `intent_debt` that the implementation cannot compute **MUST** be
reported as explicit `null`, never as `0`. A zero claims "we measured and found none"; a null
honestly says "not measured". Reporting an unmeasured signal as zero is the same class of lie as
[REC-054]'s placeholder.

**[ENV-045]** `intent_debt` **MUST** carry exactly these four components: `dark_files`,
`orphaned_intent`, `stale_decisions`, `unresolved_disputes`. Each **MUST** be a non-negative
integer, or an explicit `null` where the implementation cannot compute it ([ENV-029]). A component
**MUST NOT** be omitted.

> The last sentence is what makes [ENV-029] enforceable. Without it, an implementation that cannot
> compute `stale_decisions` satisfies the rule by dropping the key — which re-introduces the very
> ambiguity between *not applicable* and *not measured* that [ENV-038] draws, and leaves [ENV-029]
> naming no field a validator can check in either direction.

#### A.5.7 `check`

**[ENV-030]** The `check` envelope **MUST** carry `rules` (count of rules evaluated),
`files_checked`, and `violations`.

**[ENV-048]** Each entry in a `check` envelope's `violations` **MUST** carry `rule`, `file`,
`message`, and `decision_id`. A rule whose failure cannot name the decision that motivated it is
not a conformance check; it is a lint.

**[ENV-032]** A rule of a type the checker does not implement **MUST** be skipped — never counted as
a pass and never counted as a failure. Silence about an unimplementable rule is honest; a pass is
not.

#### A.5.8 `intent-diff` and `review-context`

**[ENV-033]** Both **MUST** distinguish *governed by a decision* from *governed by a constraint*.
Deterministic inspection cannot tell conformance from violation, so an implementation **MUST NOT**
report a constraint touch as a proven violation.

#### A.5.9 `capture`

**[ENV-034]** The `capture` envelope **MUST** carry `record` (the path as given, from which node
identity derives), `record_abs` (the resolved absolute destination), `node_id`, `title`,
`provenance`, `resolution_delta`, and `merged`. `record` and `record_abs` **MUST** both be reported:
the former preserves the spelling from which identity derives, while the latter makes the actual
write destination visible.

**[ENV-036]** `merged` **MUST** report whether any secondary view the implementation maintains
was updated, independently of `status`. Writing the record and failing to update such a view is an
**honest partial success**: the durable artifact exists, the view is stale. It **MUST NOT** be
reported as a failure, and **MUST NOT** be reported as an unqualified success.

**[ENV-037]** `resolution_delta` **MUST** be present with an explicit `null` when there was no
delta. This is a deliberate exception to [ENV-038] and exists because the consumer of this field is
asking a yes/no question that a missing key cannot answer.

### A.6 Transport profiles

Transport metadata is not part of a command envelope. The optional transport profile and
its schema are maintained separately in `profiles/transport.md` and
`schema/transport-envelope.schema.json`.

---
