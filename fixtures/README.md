# Whyfile conformance fixture corpus (B2)

This corpus exists so that an agent given **only** the Whyfile specification -- with no
access to the reference implementation -- can build a record parser and envelope validator
and mechanically check it against the mapped normative rules. Every fixture was verified
against the reference implementation (whyfile the reference implementation) before being written here; none of
this is copied from the project's own real decision records, which are excluded from a
public spec repo on principle (invented, neutral example content only).

## Layout

```
manifest.json        Machine-readable index: every fixture, its rule id, valid/invalid,
                      and (for invalid fixtures) exactly what must be rejected and why.
coverage.md           Human-readable rule -> valid fixture(s) -> invalid fixture(s) table.
                      Generated from the manifest and the current normative rule inventory;
                      its summary reports mapped and currently unmapped rule ids honestly.
records/              REC-* fixtures: standalone markdown decision records. Feed the raw
                      file text to your record parser; check the result against the
                      manifest entry ("parses" / "does not parse", extracted fields).
dirs/                 REC-007 (ingest-time rejected-status filtering) and several VER-*
                      fixtures that need a whole DIRECTORY of pre-existing files (the
                      filename-matching rules are directory-scoped, not single-file).
envelopes/            ENV-* fixtures: real (why/list-intent shape sanitised of internal
                      content, coverage/check as captured) and hand-authored invalid JSON
                      result envelopes.
provenance/           PROV-* fixtures: small input/output vectors for the provenance
                      trust-tier vocabulary and golden-fraction aggregation (pure
                      functions, not file parsing).
filenames/            VER-* fixtures: JSON scenario descriptors describing a directory
                      state (see dirs/) plus a capture input (chosen, question, today)
                      and the exactly-one-correct expected output filename.
```

## Rule id families

- **REC-nnn** -- record format: what makes a markdown file a decision record, and how its
  fields (title, status, alternatives, assumptions, recommendation, supersedes) parse.
- **VER-nnn** -- versioning / filename scheme: how a captured record's filename is chosen
  on first capture and matched for reuse/idempotency on every capture after that.
- **PROV-nnn** -- provenance: the trust-tier vocabulary (`authored` / `captured` /
  `attested` / `reconstructed`) and how it ranks and aggregates (golden fraction).
- **ENV-nnn** -- result envelope: the per-command JSON shape the CLI emits.

These ids are **independent of the normative spec text's own numbering** (written in
parallel by a sibling work package from the same implementation, with no visibility into
this corpus while doing so). Reconcile by the one-line `rule_statement` carried alongside
every id in `manifest.json`, not by the numbers.

## Run the retained corpus

The in-repository runner executes every manifest verdict without consulting its prose
`notes`, validates the core envelope schema and the manifest's semantic constraints, and
pins the corpus counts. Its output separates two evidence classes:

- **computed verdicts** derive an answer from fixture inputs and compare it with the
  declared expectation;
- **drift checks** compare the manifest expectation with an expected block already stored
  in the fixture. They catch two sources of truth diverging, but do not independently
  establish conformance.

Classification happens after dispatch for each fixture, so a kind such as
`render_scenario` may contribute to both classes.

```bash
python3 tools/run_corpus.py
python3 tools/run_corpus.py --check
python3 tools/run_corpus.py --write-coverage
```

`coverage.md` carries both evidence counts. `--check` exits non-zero when either count or
the rest of the generated report has drifted. The runner uses only the Python standard
library; an implementation adapter may additionally consume the same verdict shapes
described below.

## How to run an implementation against this corpus

Each fixture `kind` implies a mechanical check:

- **`record`** (`records/*.md`): feed the file's raw bytes to your record parser.
  - `valid: true` -- it MUST parse, and the manifest's `expect` object states which fields
    the result must contain (title, status, alternatives, etc.).
  - `valid: false` -- it MUST be rejected (treated as "not a record"), or in the
    finer-grained cases (REC-005/006/008/010/011) it MUST parse but with a specific field
    value named by `expect`; `valid` alone never determines that polarity.
- **`record_dir`** (`dirs/*/`): run your directory-level ingest over the whole folder.
  Each such directory carries its own `expected.json` stating the valid and invalid node
  counts/fields.
- **`filename_scenario`** (`filenames/*.json`): create the `scenario_dir` referenced in
  the JSON (its files already exist under `dirs/`), then call your filename-resolution
  function with the given `input` (`chosen`, `question`, `today`). A `valid: true` fixture
  states `expected_output` -- your function's return value MUST equal it exactly. A
  `valid: false` fixture instead states
  `wrong_output_a_non_conformant_implementation_might_return` (or an equivalent
  `wrong_*` key) plus `reason` -- your function's return value MUST NOT equal that wrong
  value (and, per the fixture's own `expected_output`/`reason`, must equal the correct one).
- **`vector`** (`provenance/*.json`): pure input/output pairs for the provenance ranking
  and golden-fraction functions. Same valid/invalid convention as above.
- **`envelope`** (`envelopes/*.json`): validate the JSON object's key set against the
  stated rule. `valid: true` -- the key set MUST be accepted. `valid: false` -- it MUST be
  rejected; the `notes` field states which key is missing/extra and why that specific
  defect is disqualifying.

`manifest.json` is the source of truth for all of the above; `coverage.md` is a derived,
human-readable view generated from it (rule -> fixtures), useful for spotting an untested
rule or an orphaned fixture at a glance.

## A note on the two rules with no invalid fixture

**REC-004** (Alternatives section is optional) and **REC-009** (ADR title-prefix
stripping) each have a valid fixture only. Both are documented, deterministic behaviours
with no reject branch: every input is either handled (REC-004: absent section -> `[]`) or
transformed exactly one correct way (REC-009: strip the prefix). There is nothing for a
parser to be right or wrong about beyond producing that one output, so a contrived
"invalid" fixture would test nothing a MUST-shaped rule requires. See `coverage.md` for
the inline explanation next to each.
