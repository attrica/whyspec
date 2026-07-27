# Proposed rules

Written while deriving `schema/parsed-record.schema.json` and `schema/envelope.schema.json`
from the specification. Each entry names a place where a schema could not state a shape
without inventing one, gives the **smallest** rule that closes it, and says what breaks if
it stays open.

**Nothing here has been applied to the specification.** Rule ids continue from the next
free ones in each family: `REC-127+`, `PROV-022+`, `ENV-044+`.

Every gap below was re-checked against the current text before being written up. **None of
the nine were already closed**; two are partially narrowed and that is noted on each.

---

## Part 1 — the nine reported gaps

### Gap 1 — an assumption node's identity components

§4.12 says "For an assumption node they are derived from the claim" and stops. It is the
one unspecified step in a section that is otherwise exact enough for an independent
implementation to land byte-identical, and there is no fixture: `identity/spec-REC-071-…`
varies the intent kind to `assumption` while reusing the decision's title as both location
and label, so the assumption path is never exercised.

> **[REC-127]** For an **assumption node**, the source location and the normalized label
> are both derived from the **claim as [REC-038] yields it** — the claim after the
> review-date and expiry strippings, whitespace-collapsed and trimmed of spaces and
> periods. Both components take that text verbatim; [REC-124] then normalizes only the
> label. `review_by` and `expiry` are **not** identity inputs.

Why this shape: it is the exact analogue of the decision node, where "source location and
label are both the record title". The last sentence is load-bearing — if the stripped
fields were inputs, editing a review date would fork the node, which is the harm
[REC-073] and [REC-076] exist to prevent.

---

### Gap 2 — what an actor is, structurally

[REC-079] gives the syntax `<role> <kind>:<id>` and [REC-080] closes both vocabularies, so
the gap is **partially narrowed**: the term has two components. What is missing is the
equality rule, and [REC-118]'s self-ratification check is defined entirely in terms of it
("the same actor also carries the role `drafted` or `decided`").

> **[REC-128]** An **actor** is the ordered pair `(kind, id)` taken from an attribution's
> `<kind>:<id>` term. Two actors are the same actor **if and only if both components are
> equal, compared as written** — no case folding, no trimming beyond [REC-079]'s parse.
> [REC-118]'s self-ratification check MUST compare the pair.

Why the pair and not the bare id: `human:alex` and `agent:alex` are the common
machine-assisted shape §4.14 describes — a person and the agent working on their behalf.
Comparing bare ids would report a self-ratification that did not occur, and [REC-118] is
the only entitlement check the format can make from the record alone; a false positive
there is worse than none.

---

### Gap 3 — an attribution carrying a malformed date

[REC-117] says a date present MUST be a full ISO-8601 calendar date. It does not say what a
parser does when it is not. The corpus fixture for a partial date asserts only that
`2026-03` and `2026-03-01` must not be yielded, and its own note records the omission.

> **[REC-129]** An attribution whose date is present but is not a full ISO-8601 calendar
> date **MUST** be yielded with its date **absent**. The malformed value **MUST NOT** be
> yielded, widened to a valid date, or repaired, and the attribution itself **MUST NOT**
> be dropped.

Why keep the attribution: dropping it would discard *who did what* because *when* was
mistyped, and [REC-120] already establishes that a weak attribution is retained rather than
deleted. Absence of the date then means what absence means everywhere else in this format —
not recorded ([REC-081], [VER-005]).

---

### Gap 4 — an unrecognized evidence method in an existing file

[REC-094] states its failure mode for the **write** path only: "a validation error at
capture time". Read-path behaviour is unstated, which leaves an implementer to choose
between yielding a fifth method (silently widening a closed set that [VER-003] says needs a
version marker) and dropping it.

> **[REC-130]** A parser reading a record whose `## Evidence` entry names a method outside
> [REC-094]'s set **MUST** drop that entry and **MUST NOT** yield the value as a method.
> Other entries in the section parse unchanged, and the record still parses: an evidence
> defect is not a record-gate defect ([REC-008]).

The alternative — retaining the entry with the method marked unrecognized — is defensible
and preserves more information, but it needs a second field, a rule for what consumers do
with it, and an answer to what happens when that value is later admitted to the set. Drop
is the smaller rule and matches how an out-of-set `<role>` or `<kind>` already has to behave.

---

### Gap 5 — which files a directory ingest considers

Nothing in the specification bounds the candidate set. The interaction the brief names is
real and testable: the corpus directory `dirs/spec-REC-001-reserved-whyfile-name/` contains
an extensionless `Whyfile` whose body is a syntactically valid decision record, and
[REC-001] requires it to contribute nothing. An implementation that feeds every file to the
parser produces two nodes where one is correct, and no rule tells it not to.

> **[REC-131]** A directory ingest **MUST** consider exactly those entries in the directory
> whose name ends in `.md` and does not begin with `.`. Every other entry — including the
> reserved bare `Whyfile` ([REC-001]) — is **not a candidate** and contributes nothing. An
> implementation **MAY** descend into subdirectories, and where it does it **MUST** apply
> this same rule at every level. A candidate that fails [REC-008] is ignored without error
> ([REC-007]).

The `.md` filter is what makes [REC-001]'s reservation self-enforcing rather than a special
case an implementer has to remember. Recursion is left a MAY because [REC-057] already
forbids inferring anything from a record's location, so depth cannot change a parse.

---

### Gap 6 — the twelve `coverage` keys

§6.1 once stated only that the summary variant carried "`command`, `status` + 12
coverage-specific keys". [ENV-044] now names all twelve, so the gap is closed.

The names below are taken from the two corpus fixtures for this variant, which the corpus
README states were verified against the reference implementation before being written.

> **[ENV-044]** The summary `coverage` variant **MUST** carry exactly these twelve
> coverage-specific keys alongside `command` and `status`: `code_files`, `code_symbols`,
> `files_with_intent`, `symbols_with_intent`, `authored_anchored_files`,
> `authored_anchored_symbols`, `file_coverage_pct`, `symbol_coverage_pct`, `dark_files`,
> `intent_by_kind`, `golden`, `intent_debt`.

⚠ **The two fixtures disagree on the type of `dark_files`** — one carries a list of paths,
the other an integer count, and both are labelled valid. The editor must pick one before
this rule is applied; the same name means "how many" in one file and "which ones" in the
other, which is the [ENV-009] defect one level down. (A count is already available inside
`intent_debt`, so the list reading is the one that adds information.)

---

### Gap 7 — `intent_debt`'s components

[ENV-029] requires an uncomputable component to be an explicit null rather than `0`, but no
rule says what the components are, so the requirement names no field a validator can check.
As written it is unenforceable in both directions: nothing says a component was omitted, and
nothing says a `0` should have been a null.

> **[ENV-045]** `intent_debt` **MUST** carry exactly these four components: `dark_files`,
> `orphaned_intent`, `stale_decisions`, `unresolved_disputes`. Each **MUST** be a
> non-negative integer, or an explicit `null` where the implementation cannot compute it
> ([ENV-029]). A component **MUST NOT** be omitted.

The last sentence is what makes [ENV-029] enforceable: without it, an implementation that
cannot compute `stale_decisions` can satisfy the rule by dropping the key, which
re-introduces the very ambiguity between *not applicable* and *not measured* that
[ENV-038] draws.

---

### Gap 8 — YAML front matter: removed, or left unparsed?

[REC-006] says front matter MUST NOT be *interpreted*, and adds "A record's meaning MUST be
fully determined by its markdown body" — which **partially narrows** the gap, but §3 never
defines a document-level "body" ([REC-004] defines only a *section's* body), so the sentence
does not decide the case.

The two readings are observably different and the corpus does not separate them: neither
front-matter fixture contains a line that the structural scanners would match. A
`# Decision: X` line inside front matter is a level-1 heading under the leave-it-alone
reading and nothing at all under the removal reading; a `**Status:** Rejected` line inside
front matter excludes the record from ingest under one reading and not the other — and
[REC-029] deliberately searches the *whole document* for that line.

> **[REC-132]** Where a document's first line is exactly `---`, the bytes from that line
> through the next line that is exactly `---`, inclusive, are **YAML front matter** and
> **MUST be removed before any other rule in §3 or §4 is applied**. A heading, status line,
> or section appearing inside front matter is therefore not structural. Where no closing
> `---` exists, the document has no front matter and is scanned whole.

Removal rather than in-place skipping is the smaller rule because it needs no exception
anywhere else: [REC-029]'s whole-document search, [REC-040]'s whole-document supersession
scan, and [REC-010]'s first-matching-H1 rule all stay exactly as written.

Note the leading-BOM tolerance of [REC-003] composes: the BOM is stripped first, so
`﻿---` opens front matter.

---

### Gap 9 — the alternative disposition separator

[REC-097] shows `<option> — <disposition>: <rationale>` with an em dash and settles nothing
else. Compare [REC-011], which enumerates its separator set explicitly for ADR headings —
the same author, the same question, answered in one place and not the other.

> **[REC-133]** In [REC-097]'s form, the separator is exactly one of em dash `—` (U+2014),
> en dash `–` (U+2013), or hyphen-minus `-`, with at least one whitespace character on each
> side. The disposition token is matched **case-insensitively** and yielded lowercased. An
> item whose token is not in [REC-098]'s closed set carries **no disposition**: [REC-099]
> applies unchanged and the whole item, separator included, is the option text.

The separator set is [REC-011]'s less the colon, which [REC-097] already spends on
introducing the rationale. Requiring whitespace on both sides is what keeps a hyphenated
option name (`blue-green deploy`) from being read as a separator. The last sentence makes
the unrecognized-token case additive rather than lossy, and is the same reasoning
[REC-099] gives: absence of a disposition means *not recorded*, never that one existed.

---

## Part 2 — inconsistencies found while deriving the schemas

These are not silences. They are two places in the document saying different things, and in
the first two cases the pair is **jointly unsatisfiable** — the same defect §6.5.2 records
having already shipped once.

### I1 — `why` results cannot satisfy [PROV-019] (`ENV-046`)

[PROV-019] requires **a result containing intent** to expose disposition. [ENV-022] was
corrected to list ten keys for a `list-intent` entry for exactly this reason, and §6.5.2
documents the correction. **[ENV-015] was not**: it enumerates thirteen keys for a `why`
result — `id`, `label`, `intent_kind`, `claim`, `rationale`, `provenance` among them, so it
plainly contains intent — and `disposition` is not one of them. Every `why` fixture in the
corpus instantiates the thirteen-key list; none carries `disposition`.

This is the one standing `FAIL` from `tools/check_schema.py`.

> **[ENV-046]** Each entry in a `why` envelope's `results` **MUST** additionally carry
> `disposition`, with the values and null convention of [ENV-022].

Without it, [PROV-020]'s presentation rule — never present foreclosure intent as what the
team does — is unenforceable on the one command whose whole purpose is answering a free-text
question, which is where a foreclosure is most likely to be read as a commitment.

### I2 — `intent_kind` is closed at two values and used with more (`ENV-047`)

[REC-122] states the intent kind "**MUST** be exactly `decision` or `assumption`". [ENV-033]
requires `intent-diff` and `review-context` to distinguish *governed by a decision* from
*governed by a **constraint***, and the corpus's `list-intent`, `why` and `coverage`
fixtures carry `intent_kind` values of `constraint`, `mechanism` and `tradeoff`. A schema
enforcing [REC-122] on the envelope field rejects three fixtures labelled valid.

The two rules are reconcilable, but only because [REC-122] is about the **identity
component** for a node derived from a record, while the envelope field describes nodes that
may have come from anywhere (§1.4 puts non-record intent out of scope). The document never
says so, and the field carries the same name in both places.

> **[ENV-047]** The envelope field `intent_kind` names the kind of the node and is **not**
> constrained to [REC-122]'s pair. [REC-122] governs the third component of node identity
> ([REC-071]) for a node derived from a record, where the only kinds are `decision` and
> `assumption`. An implementation **MUST NOT** hash any other value as that component, and
> **MUST NOT** reject an envelope carrying another value in this field.

### I3 — `alternatives` is required to be two different types (`REC-134`)

[REC-018] yields "`alternatives` — an ordered list of **strings**" and [ENV-016] repeats
"`alternatives` **MUST** be a list of strings". [REC-097]–[REC-099] require each alternative
to carry an option, an optional disposition and an optional rationale, which a string cannot
hold; the corpus asserts all three per item. `parsed-record.schema.json` states the item as
a `oneOf` **because the specification genuinely says both** — that is a report, not a design
choice.

> **[REC-134]** The `alternatives` a parser yields are **objects**, each carrying `option`
> and, where recorded, `disposition` and `rationale` ([REC-097]–[REC-099]). [REC-018]'s
> "ordered list of strings" is superseded by this rule. [ENV-016] continues to govern the
> **envelope** field `alternatives`, which projects each alternative's `option` text only;
> an implementation **MUST NOT** emit an object there.

This crosses [VER-001]: it changes how an existing section's body is parsed ([VER-003],
third and fourth bullets) and therefore needs a version marker and a migration note. §4.5.2
currently claims the disposition feature is "additive by construction" — that is true of the
*record syntax* and not of the *parse result*, and the claim should be narrowed in the same
edit.

---

## Part 3 — smaller gaps met while writing the schemas

### A1 — an empty `## Decision` body (`REC-135`)

[REC-018] makes the section required and yields `rationale` from its body. No rule says what
an empty body yields, and [REC-107] sets the opposite precedent for `question` (empty ⇒
absent, never `""`). [REC-051] speaks only to the emitter.

> **[REC-135]** A `Decision` section with an empty body yields `rationale` as an **empty
> string**, not an absent key. The section's presence is what [REC-008] tests; its
> emptiness is a fact about the record, not an absence of one.

Stated the opposite way from `question` on purpose: a record with no Decision section is not
a record at all, so an absent `rationale` key could never be observed and giving it a second
meaning would be a distinction nobody can act on.

### A2 — the key that carries a violation's decision citation (`ENV-048`)

An earlier partial rule required every violation to carry "the identifier of the decision it
cites" and named no key. [ENV-048] closes that gap with `decision_id`.

> **[ENV-048]** Each entry in a `check` envelope's `violations` **MUST** carry `rule`,
> `file`, `message`, and `decision_id` — the identifier of the decision the rule cites.

### A3 — the keys carrying §4.6.1's axes and [REC-119]'s marking (`REC-136`)

[REC-101] names two properties (deliberation state, disposition) and a third column
(offered), including the open-state marking; [REC-118] requires a
self-ratification to be "marked"; [REC-119] requires an uncorroborated ratification to be
marked. **Only `disposition` is given a key spelling by any rule** ([ENV-022]). The others
are named as obligations with no field, so two conforming implementations can both satisfy
them and share nothing.

> **[REC-136]** The properties [REC-101] determines are carried on the parsed record and the
> intent node as `deliberation` (`open` | `resolved` | `unstated`), `offered` (boolean), and
> `disposition` (`adopted` | `declined` | `null`). A self-ratification ([REC-118]) is marked
> `self_ratification` (boolean) on the record; a ratification's corroboration ([REC-119]) is
> marked `corroborated` (boolean) on the attribution.

This is the gap §8's G7 describes — no stated principle for which fields reach the output —
in its smallest concrete form. G7 is what produced the [ENV-022] defect; these are the
remaining fields it can still produce one from.

---

## Part 4 — editorial corrections (no new rule)

| Where | Says | Should say |
|---|---|---|
| [REC-031], §4.6 | "See **[ENV-026]** for the general absent-versus-null convention" | **[ENV-038]**. ENV-026 is the `changed` basename-ambiguity rule; the convention is §6.6. |
| §4.11.2, rationale under [REC-069] | "which is why **[REC-062]** derives the slug from the question in the first place" | **[REC-056]**. REC-062 is the empty-slug fallback. |
| §4.11.2, same paragraph | "**[REC-064]**'s existing-record lookup will find and update the earlier file" | **[REC-067]**. A `<today>-decision.md` destination is matched by the dated-record rule, not the legacy-name rule. |
| §8, gap G6 | "Four failure paths on the tool-call transport omit it (**[ENV-012]**)" | **[ENV-002]** is the rule broken; ENV-012 is the consumer-side corollary. §6.4 cites both correctly. |
| §7.5 | "The record identifier (§4.13), **actor** (§4.14)" | §4.14 is *Attribution*. |

### And one claim that does not hold

§4.6's "Superseded, revised" note says the earlier [REC-033] made an independent
implementation unsatisfiable because "`superseded` written as a status resolved to *open*,
therefore to no disposition, therefore to no currency — while the conformance corpus
required it to remain current", and presents the rewritten [REC-033] as the resolution.

**The rewrite does not reach that chain.** [REC-101] still routes an *unrecognized* status
to `open`, and [REC-112] still says "Currency is defined only for records whose disposition
is `adopted`; an open or declined record has no currency." A record carrying
`**Status:** Superseded` therefore still lands exactly where the note says it must not.
What [REC-033]'s rewrite fixed is the narrower contradiction with §4.6.1's own table. The
note should either be narrowed to that, or [REC-101] should exempt a status naming a
relation the graph derives.

### Corpus drift worth a separate pass

Two `expected.json` files in the fixture corpus still carry pre-revision rule text in their
`statement` fields, and one of them now conflicts with the prose:

- `dirs/spec-REC-033-only-rejected-is-normative/expected.json` states "No status value other
  than `rejected` is normative" — the exact sentence §4.6 records as having been withdrawn
  for being unsatisfiable.
- `dirs/REC-007-rejected-excluded/expected.json` expects one node from a two-record
  directory because a rejected record "must never become ground truth". [REC-104] now
  requires that record to be **retained and queryable** as foreclosure intent, and the
  corpus's own `spec-REC-104-invalid-…` fixture expects **two** nodes from the same shape.
  The two fixtures disagree with each other about the same behaviour.

§9 says a disagreement between the prose and a fixture "MUST be resolved rather than papered
over"; this is one.
