# Changelog

What changed in the specification, keyed by rule id. The specification text states rules and the
reasons for them; how a rule came to be revised is recorded here, so a reader of the rule is not
asked to read its history first. Entries are grouped by the version they belong to ([VER-009]).

## 0.1 — pre-publication baseline

Rules revised while the draft was being extracted and tested against a conformance corpus. None of
these is a meaning change under [VER-001]: the baseline had no external implementer to migrate.

- **REC-006** reversed. It first forbade interpreting front matter at all; records exist whose only
  title lives in front matter, so [REC-149] now admits `title` as a lower-precedence source and
  [REC-150] keeps `status` body-only.
- **REC-018 / REC-134**. `alternatives` was specified as a list of strings in two places while
  [REC-097]–[REC-099] required three parts per item. [REC-134] makes the parsed shape an object;
  [ENV-016] keeps the envelope projection as strings.
- **REC-030** corrected. "Its first run of lowercase alphabetic characters" read as *select the
  lowercase run*, under which `REJECTED` normalized to absent. The rule now says lowercase first,
  then select.
- **REC-033** revised. An earlier text declared no status beyond `rejected` normative, which §4.6.1
  contradicted by classifying four; the rule now defers to the table.
- **REC-107** added, resolving what was recorded as gap G3: the `Context` body is yielded as
  `question` and reaches the intent node.
- **REC-121–REC-124** added. An earlier draft named the identity's inputs and left the digest
  undefined; an independent implementation chose a different hash and produced a different id for
  every record.
- **REC-135 / REC-136** added after a round-trip audit: no record survived byte-identically, and a
  `rejected` record rendered as `accepted` because the emitter section never said which status to
  write.
- **REC-139** added: the identifier line was parsed but never rendered, and a round trip lost it.
- **REC-141** added: three obligations to "mark" a property had no key spelling.
- **REC-143 / REC-144**. The ADR section signature briefly read "all three" while every
  implementation required two; the rule and its fixtures now discriminate the case.
- **REC-158** added, resolving gap G1: fenced code blocks are quoted text. The hazard was observed —
  a record quoting its predecessor's header acquired the quoted identifier and un-retired a
  superseded record.
- **ENV-022**. The `list-intent` entry list named nine keys while [PROV-019] required a tenth,
  `disposition`; the two were jointly unsatisfiable until the list was corrected.
- **ENV-044 / ENV-045 / ENV-049 / ENV-050** added. `coverage`'s twelve keys, `intent_debt`'s four
  components, the type of `dark_files`, and `golden`'s five components were each instantiated by
  fixtures before any rule named them, and two incompatible shapes appeared for `golden`.
- **VER-009–VER-011** added, resolving gap G11: the version marker and migration table.

### Divergences of the original reference implementation

The draft was extracted from an earlier implementation and recorded where that implementation
disagreed with the text. None of these describes the current maintainer's implementation; they are
kept only as history.

- [PROV-007]: every assumption node was minted `authored` regardless of its record's kind.
- [ENV-002] / [ENV-011]: four failure paths on one transport emitted envelopes with no `command`.
- [ENV-006]: `coverage` overloaded one tag with two payloads (still the case; a future tag split is a
  meaning change).
- [REC-005]: headings and the status line were matched without excluding fenced blocks (now
  [REC-158]).
- Result field sets differed across variants describing the same nodes (now open question Q7).
