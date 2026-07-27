#!/usr/bin/env python3
"""Check that schema/*.schema.json still says what the specification's prose says.

The schemas are a SECOND statement of the field sets already written in §4, §5 and
§6. A second source of truth that can drift is worse than none — that is exactly how
the rule index went stale and had to be made generated. This script removes the
failure mode the same way build_index.py does, by re-deriving the prose side on every
run and comparing.

What it re-derives from the spec, and what it compares against:

  A  §6.1 table of top-level keys      -> each envelope variant's `required`
  B  ENV-0nn "MUST carry ..." lists    -> the same variant's / entry's `required`
  C  a rule's "MUST expose <x>"        -> every object marked x-carries-intent
  D  §6.3 table of status tokens       -> each variant's `status` enum
  E  §5.1 tier table                   -> every enum citing PROV-001
  F  "MUST be one of exactly ..."      -> the mapped enum
  G  §4.5 REC-018 "Yields" column      -> parsed-record property names
  H  every rule id cited in a schema   -> exists in the spec

Check B is the load-bearing one. The failure it exists to catch has already happened
once: [ENV-022] enumerated nine required keys for a `list-intent` entry while
[PROV-019] required a tenth, both normative, both instantiated by the corpus, and no
implementation could pass every fixture. Check C is the same pair from the other side.

    python3 tools/check_schema.py            # report; exit 1 on a real mismatch
    python3 tools/check_schema.py --verbose   # also list every check that passed

A finding whose schema location carries `x-incomplete` is reported as GAP rather than
FAIL and does not fail the run: those are places where the prose is admittedly silent
and the schema declines to invent a shape. They are tracked in schema/PROPOSED-RULES.md.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "spec" / "whyfile-spec-draft.md"
ENVELOPE = ROOT / "schema" / "envelope.schema.json"
RECORD = ROOT / "schema" / "parsed-record.schema.json"

RULE_RE = re.compile(r"^\*\*\[((?:REC|PROV|ENV|VER)-\d{3})\]\*\*(.*?)(?=\n\n)", re.M | re.S)
TICKED = re.compile(r"`([^`]+)`")
CORE = ("command", "status")

# ---------------------------------------------------------------- prose extraction


def flat(text: str) -> str:
    """One line, no bold markers — every extractor below reads this shape."""
    return " ".join(text.replace("**", "").split())


def rule_bodies(spec: str) -> dict[str, str]:
    return {m.group(1): flat(m.group(2)) for m in RULE_RE.finditer(spec)}


def table_records(spec: str, header: str) -> list[dict[str, str]]:
    """Rows keyed by their markdown column header.

    Returning only the first two cells silently redirected Check G from the
    ``Yields`` column to ``Required`` as soon as that table gained its third
    column. Header-addressed cells remain correct when columns are inserted or
    reordered, and an extractor that finds no table returns no rows so its caller
    can report a normal checker failure.
    """
    lines = spec.splitlines()
    start = next((i for i, line in enumerate(lines) if header in line), None)
    if start is None:
        return []
    headings = [
        flat(cell).replace("`", "").strip().lower()
        for cell in lines[start].strip().strip("|").split("|")
    ]
    rows: list[dict[str, str]] = []
    for line in lines[start + 2:]:
        if not line.startswith("|"):
            break
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        rows.append({
            name: flat(cells[index])
            for index, name in enumerate(headings)
            if index < len(cells)
        })
    return rows


def table_rows(spec: str, header: str) -> list[tuple[str, str]]:
    """Compatibility view of the first two named table columns."""
    records = table_records(spec, header)
    if not records:
        return []
    columns = list(records[0])
    if len(columns) < 2:
        return []
    return [
        (row.get(columns[0], "").replace("`", ""), row.get(columns[1], ""))
        for row in records
    ]


def keys_after(text: str, trigger: str, occurrence: int = 0, take: int = 0) -> list[str]:
    """Backticked identifiers between `trigger` and the first sentence end.

    Stops at a period or at a following MUST NOT, so ENV-024's "MUST carry
    `candidates` and `message` and MUST NOT carry `resolved`" does not report
    `resolved` as required. `take` bounds the count instead, for a rule that
    states two vocabularies in one sentence ([REC-101] does).
    """
    idx, pos = -1, 0
    for _ in range(occurrence + 1):
        idx = text.find(trigger, pos)
        if idx < 0:
            return []
        pos = idx + len(trigger)
    tail = text[idx + len(trigger):]
    for stop in (". ", "MUST NOT"):
        cut = tail.find(stop)
        if cut > 0:
            tail = tail[:cut]
    found = TICKED.findall(tail)
    return found[:take] if take else found


# ---------------------------------------------------------------- schema helpers


def at(schema: dict, pointer: str):
    node = schema
    for part in pointer.lstrip("#/").split("/"):
        if part:
            node = node[part.replace("~1", "/")]
    return node


def walk(node, path="#"):
    """Every (path, object) in a schema document."""
    if isinstance(node, dict):
        yield path, node
        for k, v in node.items():
            yield from walk(v, f"{path}/{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk(v, f"{path}/{i}")


# ---------------------------------------------------------------- the wiring
#
# The only hand-maintained data here is the POINTER: which part of a schema a
# given rule constrains. The key sets themselves are always read out of the prose,
# never restated, so this file cannot become the second source of truth it exists
# to prevent.

VARIANT_OF_ROW = {
    "why": "why_ok",
    "list-intent": "list_intent_ok",
    "explain (ok)": "explain_ok",
    "explain (ambiguous)": "explain_ambiguous",
    "explain (not_found)": "explain_not_found",
    "changed": "changed_ok",
    "digest": "digest_ok",
    "coverage": "coverage_summary",
    "coverage (explain form)": "coverage_explain",
    "check": "check_ok",
    "intent-diff": "intent_diff_ok",
    "review-context": "review_context_ok",
    "capture": "capture_ok",
}

# rule id, trigger phrase, occurrence, schema pointer, keys the rule takes as given
ENUMERATIONS = [
    ("ENV-013", "MUST carry:", 0, "#/$defs/why_ok", CORE),
    ("ENV-014", "be an object with", 0, "#/$defs/why_ok/properties/score_stats", ()),
    ("ENV-015", "MUST carry:", 0, "#/$defs/why_result", ()),
    ("ENV-021", "MUST carry", 0, "#/$defs/list_intent_ok", CORE),
    ("ENV-022", "MUST carry:", 0, "#/$defs/intent_entry", ()),
    ("ENV-023", "MUST carry", 0, "#/$defs/explain_ok", CORE + ("query",)),
    ("ENV-024", "MUST carry", 0, "#/$defs/explain_ambiguous", CORE + ("query",)),
    ("ENV-025", "MUST carry", 0, "#/$defs/changed_ok", CORE),
    ("ENV-025", "MUST carry", 1, "#/$defs/changed_result", ()),
    ("ENV-027", "MUST carry", 0, "#/$defs/digest_ok", CORE),
    # ENV-044 enumerates all twelve coverage-specific keys and supersedes ENV-028,
    # which names only two of them. Wiring the check to the partial rule reported a
    # gap that no longer existed — the enumeration moved, the pointer did not.
    ("ENV-044", "MUST carry exactly these twelve", 0, "#/$defs/coverage_summary", CORE),
    ("ENV-030", "MUST carry", 0, "#/$defs/check_ok", CORE),
    ("ENV-034", "MUST carry", 0, "#/$defs/capture_ok", CORE),
]

STATUS_VARIANTS = {
    "why": ["why_ok"],
    "explain": ["explain_ok", "explain_ambiguous", "explain_not_found"],
    "list-intent": ["list_intent_ok"],
    "changed": ["changed_ok"],
    "coverage": ["coverage_summary", "coverage_explain"],
    "digest": ["digest_ok"],
    "check": ["check_ok"],
    "intent-diff": ["intent_diff_ok"],
    "review-context": ["review_context_ok"],
    "capture": ["capture_ok"],
}

# rule id, trigger, occurrence, schema, pointer, how many tokens to take (0 = to the
# end of the sentence)
VOCABULARIES = [
    ("REC-080", "one of exactly", 0, RECORD, "#/$defs/attribution/properties/kind", 0),
    ("REC-080", "one of exactly", 1, RECORD, "#/$defs/attribution/properties/role", 0),
    ("REC-088", "one of exactly", 0, RECORD, "#/$defs/relation/properties/relation", 0),
    ("REC-094", "one of exactly", 0, RECORD, "#/$defs/evidence/properties/method", 0),
    ("REC-098", "one of exactly", 0, RECORD, "#/$defs/alternative/properties/disposition", 0),
    ("REC-101", "deliberation state", 0, RECORD, "#/properties/deliberation", 2),
    ("REC-101", "a disposition", 0, RECORD, "#/properties/disposition", 2),
    ("REC-122", "MUST be exactly", 0, RECORD, "#/properties/intent_kind", 0),
]


# ---------------------------------------------------------------- the checks


class Report:
    def __init__(self) -> None:
        self.fail: list[str] = []
        self.gap: list[str] = []
        self.ok = 0

    def check(self, condition: bool, message: str, known_gap: bool = False) -> None:
        if condition:
            self.ok += 1
        elif known_gap:
            self.gap.append(message)
        else:
            self.fail.append(message)


def incomplete(node: dict) -> bool:
    return "x-incomplete" in node


def check_top_level_keys(spec: str, env: dict, rep: Report) -> None:
    """A — §6.1's table of top-level keys against each variant's `required`."""
    for label, cell in table_rows(spec, "| `command` | Top-level keys |"):
        variant = VARIANT_OF_ROW.get(label)
        if variant is None:
            rep.fail.append(f"A §6.1 names command row {label!r}, which no schema variant covers")
            continue
        node = at(env, f"#/$defs/{variant}")
        want_required = set(node.get("required", []))

        count = re.search(r"\+ (\d+) [\w-]+ keys", cell)
        if count:                                    # "command, status + 12 ... keys"
            total = len(TICKED.findall(cell)) + int(count.group(1))
            named = len(want_required)
            rep.check(
                node.get("minProperties") == total,
                f"A {label}: §6.1 requires {total} top-level keys; "
                f"schema minProperties={node.get('minProperties')}",
                incomplete(node),
            )
            rep.check(
                named == total,
                f"A {label}: §6.1 requires {total} top-level keys but only {named} "
                f"({', '.join(sorted(want_required))}) are named by any rule — "
                f"{total - named} unnamed",
                incomplete(node),
            )
            continue

        prose = TICKED.findall(cell)
        if "when and only when" in cell:             # `why`'s conditional `note`
            head = TICKED.findall(cell.split("when and only when")[0])
            conditional, prose = head[-1], head[:-1]
            then = node.get("then", {}).get("required", [])
            rep.check(
                conditional in then,
                f"A {label}: §6.1 makes {conditional!r} conditional; "
                f"schema's conditional `required` is {then}",
            )
        rep.check(
            set(prose) == want_required,
            f"A {label}: §6.1 says {sorted(set(prose))}; schema requires {sorted(want_required)}",
        )


def check_enumerations(rules: dict, env: dict, rep: Report) -> None:
    """B — each ENV-0nn "MUST carry ..." list against the schema it constrains."""
    for rule, trigger, occ, pointer, given in ENUMERATIONS:
        body = rules.get(rule)
        if body is None:
            rep.fail.append(f"B {rule} not found in the spec")
            continue
        prose = set(keys_after(body, trigger, occ)) | set(given)
        node = at(env, pointer)
        rep.check(
            prose == set(node.get("required", [])),
            f"B [{rule}] enumerates {sorted(prose)}; {pointer} requires "
            f"{sorted(node.get('required', []))}",
            incomplete(node),
        )
        if "MUST NOT carry" in body:
            forbidden = set(keys_after(body, "MUST NOT carry", 0))
            rep.check(
                forbidden <= set(node.get("not", {}).get("required", [])),
                f"B [{rule}] forbids {sorted(forbidden)}; {pointer} forbids "
                f"{sorted(node.get('not', {}).get('required', []))}",
            )


def check_must_expose(rules: dict, env: dict, rep: Report) -> None:
    """C — a rule demanding a field on "a result containing intent".

    This is the cross-rule direction of the failure that already shipped: an
    obligation stated in one section that the section enumerating the output never
    picked up. It fails if any object marked x-carries-intent omits the field.
    """
    demands = {
        (rid, m.group(1))
        for rid, body in rules.items()
        for m in re.finditer(r"MUST expose ([a-z_]+)", body)
    }
    carriers = [(p, n) for p, n in walk(env) if n.get("x-carries-intent")]
    rep.check(bool(carriers), "C no schema object is marked x-carries-intent")
    for rid, field in sorted(demands):
        for path, node in carriers:
            rep.check(
                field in node.get("required", []),
                f"C [{rid}] requires {field!r} on a result containing intent; "
                f"{path} requires {sorted(node.get('required', []))}",
            )


def check_status_tokens(spec: str, env: dict, rep: Report) -> None:
    """D — §6.3's per-command status tokens against each variant's `status` enum."""
    rows = dict(table_rows(spec, "| `command` | Status tokens |"))
    universal = set(TICKED.findall(rows.get("any (input failure)", "")))
    rep.check(bool(universal), "D §6.3 has no 'any (input failure)' row")
    for command, variants in STATUS_VARIANTS.items():
        prose = set(TICKED.findall(rows.get(command, "")))
        rep.check(bool(prose), f"D §6.3 lists no status tokens for {command!r}")
        allowed = set(universal)
        for v in variants:
            enum = at(env, f"#/$defs/{v}/properties/status")
            allowed |= set(enum.get("enum", [])) | ({enum["const"]} if "const" in enum else set())
        rep.check(
            prose <= allowed,
            f"D {command}: §6.3 lists {sorted(prose - allowed)} which no variant's "
            f"status enum accepts (schema allows {sorted(allowed)})",
        )


def check_tiers(spec: str, schemas: dict[str, dict], rep: Report) -> None:
    """E — §5.1's tier table against every enum whose x-rule cites PROV-001."""
    tiers = {label for label, _ in table_rows(spec, "| Tier | What it means |")}
    rep.check(len(tiers) == 4, f"E §5.1 lists {len(tiers)} tiers, expected 4")
    found = 0
    for name, schema in schemas.items():
        for path, node in walk(schema):
            if "PROV-001" in node.get("x-rule", []) and "enum" in node:
                found += 1
                rep.check(
                    set(node["enum"]) == tiers,
                    f"E {name}{path}: enum {sorted(node['enum'])} != §5.1 tiers {sorted(tiers)}",
                )
    rep.check(found > 0, "E no enum cites PROV-001")




def span_of(rule: str) -> str:
    """Everything from a rule's marker to the next rule marker or heading.

    `RULE_RE` deliberately stops at the first blank line, which is right for a
    one-paragraph rule and wrong for one whose normative content is a table.
    """
    import re as _re
    text = SPEC.read_text()
    m = _re.search(
        r"\*\*\[" + _re.escape(rule) + r"\]\*\*(.*?)(?=\n\*\*\[(?:REC|PROV|ENV|VER)-\d{3}\]|\n#{2,4} )",
        text, _re.S)
    return m.group(1) if m else ""


def column_values(body: str, header: str) -> list[str]:
    """Distinct values of a markdown table column, matched by header substring.

    Cells may carry emphasis or an em-dash placeholder; both are stripped, and the
    placeholder is dropped rather than returned as a vocabulary member.
    """
    rows = [r for r in body.splitlines() if r.lstrip().startswith("|")]
    if len(rows) < 2:
        return []
    heads = [c.strip().strip("*`").lower() for c in rows[0].strip("|").split("|")]
    # match on the header's most specific word, not its first — a trigger phrased
    # "a disposition" would otherwise match any column containing "a".
    want = max(header.lower().split(), key=len)
    idx = next((i for i, h in enumerate(heads) if want in h), None)
    if idx is None:
        return []
    out = []
    for r in rows[2:]:                       # skip the header separator row
        cells = [c.strip() for c in r.strip("|").split("|")]
        if idx >= len(cells):
            continue
        v = cells[idx].strip().strip("*`_ ")
        if v and v not in {"—", "-", "n/a"} and v not in out:
            out.append(v)
    return out


def check_vocabularies(rules: dict, schemas: dict[Path, dict], rep: Report) -> None:
    """F — closed vocabularies stated in a rule against the enum they constrain."""
    for rule, trigger, occ, path, pointer, take in VOCABULARIES:
        body = rules.get(rule)
        if body is None:
            rep.fail.append(f"F {rule} not found in the spec")
            continue
        prose = set(keys_after(body, trigger, occ, take))
        if not prose:
            # REC-101 now states its vocabularies as TABLE COLUMNS rather than in a
            # sentence, because six scattered rules kept drifting apart. A rule body
            # stops at the first blank line, so the table sits outside it — harvest
            # from the rule's full span instead. An extractor that silently finds
            # nothing turns a real check into a vacuous pass, worse than a failure.
            prose = set(column_values(span_of(rule), trigger))
        node = at(schemas[path], pointer)
        enum = set(node.get("enum", []))
        vocabulary = {value for value in enum if value is not None}
        rep.check(
            bool(prose) and prose == vocabulary,
            f"F [{rule}] states {sorted(prose)}; {pointer} enumerates "
            f"{sorted(vocabulary)}",
        )


def check_section_yields(spec: str, record: dict, rep: Report) -> None:
    """G — REC-018's "Yields" column against parsed-record property names."""
    props = record["properties"]
    rows = table_records(spec, "| Heading |")
    rep.check(bool(rows), "G REC-018's section table was not found")
    for row in rows:
        cell = row.get("yields", "")
        for field in TICKED.findall(cell):
            if field in ("REC-021",) or field.startswith("§"):
                continue
            rep.check(
                field in props,
                f"G REC-018 says a section yields {field!r}; parsed-record has no "
                f"such property",
            )


def check_citations(rules: dict, schemas: dict[str, dict], rep: Report) -> None:
    """H — every rule id a schema cites exists, and every property cites one."""
    known = set(rules)
    for name, schema in schemas.items():
        for path, node in walk(schema):
            for rid in node.get("x-rule", []):
                rep.check(rid in known, f"H {name}{path} cites {rid}, which is not a rule")
            parent = path.rsplit("/", 2)[-2] if path.count("/") >= 2 else ""
            if parent == "properties" and "description" in node:
                rep.check(
                    bool(node.get("x-rule")),
                    f"H {name}{path} is a property with no x-rule",
                )
                cited = re.findall(r"(?:REC|PROV|ENV|VER)-\d{3}", node.get("description", ""))
                rep.check(
                    bool(cited),
                    f"H {name}{path} description cites no rule id",
                )
                for rid in cited:
                    rep.check(rid in known, f"H {name}{path} description cites unknown {rid}")


# ---------------------------------------------------------------- entry point


def main() -> int:
    spec = SPEC.read_text()
    rules = rule_bodies(spec)
    env = json.loads(ENVELOPE.read_text())
    record = json.loads(RECORD.read_text())
    by_name = {"envelope": env, "parsed-record": record}
    by_path = {ENVELOPE: env, RECORD: record}

    rep = Report()
    check_top_level_keys(spec, env, rep)
    check_enumerations(rules, env, rep)
    check_must_expose(rules, env, rep)
    check_status_tokens(spec, env, rep)
    check_tiers(spec, by_name, rep)
    check_vocabularies(rules, by_path, rep)
    check_section_yields(spec, record, rep)
    check_citations(rules, by_name, rep)

    for line in rep.gap:
        print(f"GAP  {line}")
    for line in rep.fail:
        print(f"FAIL {line}")
    print(f"\n{rep.ok} check(s) passed, {len(rep.fail)} failed, "
          f"{len(rep.gap)} known gap(s), over {len(rules)} rule bodies")
    if rep.gap:
        print("known gaps are places the prose is silent — see schema/PROPOSED-RULES.md")
    return 1 if rep.fail else 0


def demo() -> None:
    """Self-check: the checker must catch the failure that already shipped.

    [ENV-022] plus [PROV-019] require ten keys on a list-intent entry. Drop the
    tenth and both check B and check C must fire; if either stays silent the
    schema can drift from the prose again and this tool is decoration.
    """
    spec = SPEC.read_text()
    rules = rule_bodies(spec)
    env = json.loads(ENVELOPE.read_text())
    entry = env["$defs"]["intent_entry"]
    entry["required"] = [k for k in entry["required"] if k != "disposition"]

    b, c = Report(), Report()
    check_enumerations(rules, env, b)
    check_must_expose(rules, env, c)
    assert any("ENV-022" in f for f in b.fail), "check B missed the dropped key"
    assert any("PROV-019" in f for f in c.fail), "check C missed the dropped key"
    print("demo ok — dropping `disposition` fails both check B and check C")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo()
        raise SystemExit(0)
    raise SystemExit(main())
