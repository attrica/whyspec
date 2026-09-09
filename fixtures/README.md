# Whyspec conformance fixture corpus

This corpus exists so that an implementer given **only** the Whyspec specification can build a
record parser and envelope validator and mechanically check it against the mapped normative
rules. Every fixture's expectation is executable from the manifest alone. All example content is
invented and neutral.

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
dirs/                 Directory-level fixtures: rejected-record handling and the FIL-*
                      filename rules, which need a whole DIRECTORY of pre-existing files
                      (the filename-matching rules are directory-scoped, not single-file).
envelopes/            ENV-* fixtures: example JSON result envelopes, valid and invalid.
provenance/           PROV-* fixtures: small input/output vectors for the provenance
                      trust-tier vocabulary and golden-fraction aggregation (pure
                      functions, not file parsing).
filenames/            FIL-* fixtures: JSON scenario descriptors describing a directory
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

These ids are **independent of the normative spec text's own numbering**. Reconcile through
`spec_rule_ids` and the one-line `rule_statement` carried alongside every id in
`manifest.json`, never by matching numbers.

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

### Expectation keys are not the field set

The keys inside an `expect` object are a vocabulary about **parser behaviour**, and they are
deliberately wider than the fields a parsed record serializes. Most of them name no field at
all: `parses` is asserted by nearly every record fixture and is not a field; neither are
`governs_declared`, `evidence_declared`, `attribution_recorded`, the `engine_*` keys of the
differential fixtures, or the counts and projections several rules are tested through. An
implementation reading this corpus computes them; it does not store them.

So a key with no matching field in `schema/parsed-record.schema.json` is **not** by itself a
defect. The test a key has to pass is different: **the concept it asserts must be defined by a
rule**, even where the key itself is not a field. `governs_declared` passes because [REC-084]
defines scope-not-declared as a distinct state. A key asserting something no rule defines does
not pass, because an implementer working from the published text alone would write a conforming
parser and still fail here, with no rule to read that tells them why.

One further test, and it is the one that is easy to miss: a key must not be **redundant with a
field**. Where a value is a function of a field the specification already defines, the fixture
asserts the field and the implementation derives the rest. This is [REC-111]'s reasoning about
currency applied to the corpus — a stored value that could be derived goes stale in a way a
derived one cannot — and two keys were removed under it after they had already shipped.

## A note on the two rules with no invalid fixture

corpus **REC-004** (Alternatives section is optional) and corpus **REC-009** (ADR title-prefix
stripping) each have a valid fixture only. Both are documented, deterministic behaviours
with no reject branch: every input is either handled (REC-004: absent section -> `[]`) or
transformed exactly one correct way (REC-009: strip the prefix). There is nothing for a
parser to be right or wrong about beyond producing that one output, so a contrived
"invalid" fixture would test nothing a MUST-shaped rule requires. See `coverage.md` for
the inline explanation next to each.
