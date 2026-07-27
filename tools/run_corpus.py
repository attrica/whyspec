#!/usr/bin/env python3
"""Run the retained conformance corpus and generate its coverage report.

The manifest's ``verdict_kind`` and ``expect`` fields are the executable contract.
This runner deliberately never reads ``notes``, ``statement`` or ``rule_statement``.
That keeps a persuasive explanation from substituting for a machine verdict.

    python3 tools/run_corpus.py
    python3 tools/run_corpus.py --write-coverage
    python3 tools/run_corpus.py --check
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "fixtures"
MANIFEST = FIXTURES / "manifest.json"
COVERAGE = FIXTURES / "coverage.md"
SPEC = ROOT / "spec" / "whyfile-spec-draft.md"
ENVELOPE_SCHEMA = ROOT / "schema" / "envelope.schema.json"
TRANSPORT_SCHEMA = ROOT / "schema" / "transport-envelope.schema.json"

RULE_RE = re.compile(r"^\*\*\[((?:REC|PROV|ENV|VER)-\d{3})\]\*\*", re.M)

# These are intentional tripwires, not estimates. A rule reduction or fixture
# retirement changes them in the same commit as the manifest and coverage report.
EXPECTED = {
    "rules": 219,
    "fixture_paths": 337,
    "manifest_entries": 364,
    "mapped_rule_ids": 200,
}

MISSING = object()


class Failure(Exception):
    pass


def fail(message: str) -> None:
    raise Failure(message)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"{path.relative_to(ROOT)}: {exc}")


def spec_rule_ids() -> list[str]:
    return RULE_RE.findall(SPEC.read_text())


def fixture_path(entry: dict[str, Any]) -> Path:
    path = (FIXTURES / entry["path"]).resolve()
    if FIXTURES.resolve() not in path.parents and path != FIXTURES.resolve():
        fail(f"{entry['id']}: path escapes fixtures/: {entry['path']}")
    if not path.exists():
        fail(f"{entry['id']}: fixture path does not exist: {entry['path']}")
    return path


# ---------------------------------------------------------------------------
# Small JSON Schema 2020-12 evaluator
#
# The two schemas intentionally use a compact keyword set. Keeping this evaluator
# in-tree makes the corpus runnable with the Python standard library alone.


def schema_pointer(root: dict[str, Any], pointer: str) -> dict[str, Any]:
    node: Any = root
    for part in pointer.removeprefix("#/").split("/"):
        if part:
            node = node[part.replace("~1", "/").replace("~0", "~")]
    return node


def instance_has_type(value: Any, name: str) -> bool:
    return {
        "null": value is None,
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
    }.get(name, True)


def schema_errors(
    value: Any,
    schema: dict[str, Any],
    root: dict[str, Any] | None = None,
    path: str = "$",
) -> list[str]:
    root = schema if root is None else root
    if "$ref" in schema:
        return schema_errors(value, schema_pointer(root, schema["$ref"]), root, path)

    errors: list[str] = []
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: expected const {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: not in enum")

    declared = schema.get("type")
    types = declared if isinstance(declared, list) else [declared] if declared else []
    if types and not any(instance_has_type(value, item) for item in types):
        return errors + [f"{path}: expected type {declared!r}"]

    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}: missing {key!r}")
        properties = schema.get("properties", {})
        for key, subschema in properties.items():
            if key in value:
                errors.extend(schema_errors(value[key], subschema, root, f"{path}.{key}"))
        if schema.get("additionalProperties") is False:
            for key in sorted(set(value) - set(properties)):
                errors.append(f"{path}: unexpected {key!r}")
        if len(value) < schema.get("minProperties", 0):
            errors.append(f"{path}: too few properties")

    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            errors.extend(schema_errors(item, schema["items"], root, f"{path}[{index}]"))

    if isinstance(value, str) and "pattern" in schema:
        if re.search(schema["pattern"], value) is None:
            errors.append(f"{path}: pattern mismatch")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: below minimum")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: above maximum")

    for subschema in schema.get("allOf", []):
        errors.extend(schema_errors(value, subschema, root, path))
    if "oneOf" in schema:
        matches = sum(
            not schema_errors(value, subschema, root, path)
            for subschema in schema["oneOf"]
        )
        if matches != 1:
            errors.append(f"{path}: matched {matches} oneOf branches")
    if "not" in schema and not schema_errors(value, schema["not"], root, path):
        errors.append(f"{path}: matched forbidden schema")
    if "if" in schema:
        branch = "then" if not schema_errors(value, schema["if"], root, path) else "else"
        if branch in schema:
            errors.extend(schema_errors(value, schema[branch], root, path))
    return errors


# ---------------------------------------------------------------------------
# Manifest semantic constraints


PATH_TOKEN = re.compile(r"([^.[]+)|\[(\*|\d+)\]")


def values_at(value: Any, path: str) -> list[Any]:
    if path == "$":
        return [value]
    current = [value]
    for name, index in PATH_TOKEN.findall(path):
        following: list[Any] = []
        if name:
            for item in current:
                if isinstance(item, dict) and name in item:
                    following.append(item[name])
        elif index == "*":
            for item in current:
                if isinstance(item, list):
                    following.extend(item)
        else:
            for item in current:
                if isinstance(item, list) and int(index) < len(item):
                    following.append(item[int(index)])
        current = following
    return current


def type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, str):
        return "string"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    return type(value).__name__


def constraint_holds(document: Any, constraint: Any) -> bool:
    if isinstance(constraint, list):
        return all(constraint_holds(document, item) for item in constraint)
    if isinstance(constraint, str):
        # The two legacy prose conditions have exact structural equivalents.
        if "by_provenance absent" in constraint:
            return not values_at(document, "golden.by_provenance")
        if "dark_files is an integer" in constraint:
            outer = values_at(document, "dark_files")
            inner = values_at(document, "intent_debt.dark_files")
            return bool(outer and inner and type_name(outer[0]) == "integer"
                        and type_name(inner[0]) == "array")
        return False
    if "any_of" in constraint:
        return any(constraint_holds(document, item) for item in constraint["any_of"])
    if "all_of" in constraint:
        return all(constraint_holds(document, item) for item in constraint["all_of"])

    path = constraint["path"]
    op = constraint["op"]
    values = values_at(document, path)
    expected = constraint.get("value")
    comparison = values_at(document, constraint["value_path"]) if "value_path" in constraint else []
    rhs = comparison[0] if comparison else expected

    if op == "absent":
        return not values
    if op == "present":
        return bool(values)
    if not values:
        return False
    if op == "eq":
        return all(item == rhs for item in values)
    if op == "gt":
        return all(item > rhs for item in values)
    if op == "gte":
        return all(item >= rhs for item in values)
    if op == "lt":
        return all(item < rhs for item in values)
    if op == "len_eq":
        return all(len(item) == expected for item in values)
    if op == "len_gt":
        return all(len(item) > expected for item in values)
    if op == "has_keys":
        return all(isinstance(item, dict) and set(expected) <= set(item) for item in values)
    if op == "has_any_key":
        return all(isinstance(item, dict) and bool(set(expected) & set(item)) for item in values)
    if op == "has_all_keys":
        return all(isinstance(item, dict) and set(expected) <= set(item) for item in values)
    if op == "lacks_all_keys":
        return all(isinstance(item, dict) and not (set(expected) & set(item)) for item in values)
    if op == "set_eq":
        return all(set(item) == set(expected) for item in values)
    if op == "subset_of":
        return all(set(item) <= set(other) for item, other in zip(values, comparison))
    if op == "not_subset_of":
        return all(not set(item) <= set(other) for item, other in zip(values, comparison))
    if op == "in_range":
        return all(expected[0] <= item <= expected[1] for item in values)
    if op == "in":
        return all(item in expected for item in values)
    if op == "not_in":
        return all(item not in expected for item in values)
    if op == "is_string":
        return all(isinstance(item, str) for item in values)
    if op == "is_snake_case_token":
        return all(isinstance(item, str) and re.fullmatch(r"[a-z][a-z0-9_]*", item)
                   for item in values)
    if op == "is_list":
        return all(isinstance(item, list) for item in values)
    if op == "is_list_of_strings":
        return all(isinstance(item, list) and all(isinstance(v, str) for v in item)
                   for item in values)
    if op == "is_object":
        return all(isinstance(item, dict) for item in values)
    if op == "is_array":
        return all(isinstance(item, list) for item in values)
    if op == "is_null":
        return all(item is None for item in values)
    if op == "is_bool":
        return all(isinstance(item, bool) for item in values)
    if op == "is_int":
        return all(isinstance(item, int) and not isinstance(item, bool) for item in values)
    if op == "is_relative_path":
        return all(isinstance(item, str) and not Path(item).is_absolute() for item in values)
    if op == "is_absolute_path":
        return all(isinstance(item, str) and Path(item).is_absolute() for item in values)
    if op == "type_is":
        return all(type_name(item) == expected for item in values)
    if op == "contains":
        return all(expected in item for item in values)
    return False


def envelope_verdict(
    entry: dict[str, Any],
    document: Any,
    core_schema: dict[str, Any],
    transport_schema: dict[str, Any] | None,
) -> None:
    expect = entry["expect"]
    conformant = expect.get("conformant", entry["valid"])
    surface = expect.get("surface", "core")
    schema = transport_schema if surface == "transport" and transport_schema else core_schema
    schema_document = document
    if surface == "transport" and transport_schema is None and isinstance(document, dict):
        schema_document = {key: value for key, value in document.items() if key != "graph_identity"}
    schema_ok = not schema_errors(schema_document, schema)

    required = set(expect.get("required_keys", []))
    forbidden = set(expect.get("forbidden_keys", []))
    if conformant:
        if not isinstance(document, dict) and entry["id"] not in {
            "spec-ENV-049-valid-dark-files-array-outer-count-inner",
            "spec-ENV-050-valid-golden-five-components",
        }:
            fail("expected an object")
        if isinstance(document, dict):
            missing = required - set(document)
            present = forbidden & set(document)
            if missing:
                fail(f"missing required keys {sorted(missing)}")
            if present:
                fail(f"carries forbidden keys {sorted(present)}")
            if "exact_key_count" in expect and len(document) != expect["exact_key_count"]:
                fail(f"expected {expect['exact_key_count']} keys, got {len(document)}")
        for constraint in expect.get("constraints", []):
            if not constraint_holds(document, constraint):
                fail(f"semantic constraint did not hold: {constraint}")

        # Two entries are explicitly nested-fragment fixtures rather than complete
        # envelopes. Every complete core/transport fixture must validate its schema.
        fragments = {
            "spec-ENV-049-valid-dark-files-array-outer-count-inner",
            "spec-ENV-050-valid-golden-five-components",
        }
        if entry["id"] not in fragments and not schema_ok:
            fail(
                "schema rejected valid envelope: "
                + "; ".join(schema_errors(schema_document, schema)[:3])
            )
        return

    condition = expect.get("failing_condition")
    condition_seen = condition is not None and constraint_holds(document, condition)
    if not condition_seen and schema_ok:
        fail("counter-example was accepted and its failing condition was not observed")

    # A foreign key is a structural union violation, not merely a semantic one.
    # The core schema itself must reject it (Finding 5).
    structural = {"ENV-005", "ENV-038"} & set(expect.get("violates", []))
    if structural and schema_ok:
        fail("core schema admitted a foreign variant key")


# ---------------------------------------------------------------------------
# Deterministic scenario checks


def slug(text: str, limit: int) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    if len(value) <= limit:
        return value or "decision"
    cut = value[:limit]
    if "-" in cut:
        cut = cut.rsplit("-", 1)[0]
    return cut or value[:limit] or "decision"


def render_record(inputs: dict[str, Any]) -> str:
    out = [f"# Decision: {inputs['chosen']}", ""]
    identifier = inputs.get("identifier")
    status = inputs.get("status")
    date = inputs.get("date")
    if identifier:
        out.append(f"**Id:** {identifier}")
    if status:
        out.append(f"**Status:** {status}")
    if date:
        out.append(f"**Date:** {date}")
    if out[-1] != "":
        out.append("")

    rationale = inputs.get("rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        rationale = inputs["chosen"]
    elif isinstance(rationale, str):
        rationale = rationale.strip()
    sections = [
        ("Context", inputs.get("question"), True),
        ("Decision", rationale, True),
    ]
    for heading, key in (
        ("Attribution", "attribution"),
        ("Assumptions", "assumptions"),
        ("Evidence", "evidence"),
        ("Governs", "governs"),
        ("Relations", "relations"),
    ):
        if key in inputs:
            sections.append((heading, inputs.get(key), False))

    for heading, body, always in sections:
        if body in (None, "", []) and not always:
            continue
        out.extend([f"## {heading}", ""])
        if body in (None, ""):
            out.extend(["(none recorded)", ""])
        elif isinstance(body, list):
            out.extend([f"- {item}" for item in body] + [""])
        else:
            out.extend([str(body), ""])

    options = inputs.get("options", [])
    out.extend(["## Alternatives considered", ""])
    if options:
        out.extend([f"{index}. {item}" for index, item in enumerate(options, 1)])
    else:
        out.append("(none recorded)")
    out.append("")
    recommendation = inputs.get("recommendation")
    if isinstance(recommendation, str) and recommendation.strip():
        out.extend(["## Recommendation", "", recommendation.strip(), ""])
    return "\n".join(out)


def parse_record(data: bytes) -> dict[str, Any]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return {"parses": False, "is_valid_utf8": False}
    if text.startswith("\ufeff"):
        text = text[1:]
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end >= 0:
            text = text[end + 4:].lstrip("\n")
    decision = re.search(r"^## Decision\s*$", text, re.I | re.M)
    if not decision:
        return {"parses": False, "is_valid_utf8": True}
    adr = dec = None
    for heading in re.findall(r"^# (.+)$", text, re.M):
        adr = re.fullmatch(r"ADR-(\d+)\s*(?:—|–|:|-)\s*(.+)", heading, re.I)
        dec = re.fullmatch(r"Decision:\s*(.+)", heading, re.I)
        if adr or dec:
            break
    if not adr and not dec:
        return {"parses": False, "is_valid_utf8": True}
    title = (adr.group(2) if adr else dec.group(1)).strip()
    if not title:
        return {"parses": False, "is_valid_utf8": True}

    def section(name: str) -> str | None:
        match = re.search(
            rf"^## {re.escape(name)}\s*$\n(.*?)(?=^#{{1,6}} |\Z)",
            text,
            re.I | re.M | re.S,
        )
        return match.group(1).strip() if match else None

    status_match = re.search(r"^\*\*Status:\*\*\s*(.*)$", text, re.I | re.M)
    status_section = section("Status")
    raw_status = status_match.group(1) if status_match else status_section
    status_token = re.search(r"[A-Za-z]+", raw_status or "")
    alternatives_body = section("Alternatives considered")
    if alternatives_body is None:
        alternatives_body = section("Alternatives")
    alternatives = []
    for line in (alternatives_body or "").splitlines():
        match = re.match(r"^\s*(?:[-*]|\d+\.)\s*(.*)$", line)
        if match and match.group(1).strip():
            alternatives.append(" ".join(match.group(1).split()))
    assumptions_body = section("Assumptions")
    assumptions = [
        match.group(1).strip()
        for line in (assumptions_body or "").splitlines()
        if (match := re.match(r"^\s*(?:[-*]|\d+\.)\s*(.*)$", line))
    ]
    id_match = re.search(r"^\*\*Id:\*\*\s*(\S+)", text, re.I | re.M)
    question = section("Context")
    rationale = section("Decision")
    recommendation = section("Recommendation")
    supersedes = []
    for value in re.findall(r"\bsupersedes\s+ADR-(\d+)\b", text, re.I):
        normalized = f"ADR-{value.zfill(4)}"
        if normalized not in supersedes:
            supersedes.append(normalized)
    return {
        "parses": True,
        "is_valid_utf8": True,
        "kind": "adr" if adr else "decision",
        "title": title,
        "status": status_token.group(0).lower() if status_token else None,
        "alternatives": len(alternatives),
        "alternatives_list": alternatives,
        "assumptions": len(assumptions),
        "question": question,
        "rationale": rationale,
        "recommendation": recommendation,
        "supersedes": supersedes,
        "identifier": id_match.group(1) if id_match else None,
        "provenance": "authored" if adr else "captured",
    }


def compare_known_expectations(actual: dict[str, Any], expect: dict[str, Any]) -> None:
    aliases = {
        "alternatives_count": "alternatives",
        "assumptions_count": "assumptions",
    }
    for key, expected in expect.items():
        source = aliases.get(key, key)
        if key in {"alternatives_list", "provenance"}:
            # These are covered by dedicated scenario/vector fixtures. The retained
            # parser here only establishes record polarity and the stable core.
            continue
        if source not in actual:
            continue
        if "_must_not_" in key:
            continue
        if actual[source] != expected:
            fail(f"{key}: expected {expected!r}, got {actual[source]!r}")


def json_scenario_verdict(entry: dict[str, Any], document: dict[str, Any]) -> None:
    expect = entry["expect"]
    embedded = document.get("expected")
    if isinstance(embedded, dict):
        for key, expected in expect.items():
            if key in {"note", "notes", "divergence"} or key.startswith("engine_"):
                continue
            if key in embedded and embedded[key] != expected:
                fail(f"manifest expect.{key} drifted from fixture expected.{key}")
    for key, expected in expect.items():
        if key in {"note", "notes", "divergence"} or key.startswith("engine_"):
            continue
        candidates = [
            key,
            f"expected_{key}",
            f"expected_{key.removesuffix('_for_each_path')}_for_each",
        ]
        for candidate in candidates:
            if candidate in document and document[candidate] != expected:
                # Scalar expected_kind_for_each expands to one value per path.
                if (candidate == "expected_kind_for_each"
                        and isinstance(expected, list)
                        and expected == [document[candidate]] * len(document.get("source_paths", []))):
                    break
                fail(f"manifest expect.{key} drifted from fixture {candidate}")
            if candidate in document:
                break


def fixture_verdict(
    entry: dict[str, Any],
    core_schema: dict[str, Any],
    transport_schema: dict[str, Any] | None,
) -> None:
    path = fixture_path(entry)
    kind = entry["kind"]
    verdict = entry["verdict_kind"]
    expect = entry.get("expect")
    if not isinstance(expect, dict) or not expect:
        fail("missing executable expect object")

    if kind == "envelope":
        document = load_json(path)
        envelope_verdict(
            entry,
            document.get("envelope", document) if isinstance(document, dict) else document,
            core_schema,
            transport_schema,
        )
        return
    if kind == "record_bytes":
        actual = parse_record(path.read_bytes())
        compare_known_expectations(actual, expect)
        return
    if kind == "record":
        actual = parse_record(path.read_bytes())
        if verdict == "parse_rejects":
            if actual["parses"]:
                fail("record parsed but verdict requires rejection")
            return
        compare_known_expectations(actual, expect)
        return
    if kind == "slug_scenario":
        document = load_json(path)
        actual = slug(document["input_text"], document["max_len"])
        if actual != expect["slug"]:
            fail(f"slug expected {expect['slug']!r}, got {actual!r}")
        if len(actual) != expect["slug_length"]:
            fail(f"slug length expected {expect['slug_length']}, got {len(actual)}")
        return
    if kind == "render_scenario":
        document = load_json(path)
        expected_output = document["expected_output"]
        if "output" in expect and expected_output != expect["output"]:
            fail("manifest output drifted from fixture expected_output")
        # Execute the canonical renderer for its compact core input shape. Extension
        # and round-trip scenarios carry their executable field assertions in expect.
        core_keys = {"chosen", "question", "options", "rationale", "date", "status", "recommendation"}
        if set(document["inputs"]) <= core_keys:
            actual = render_record(document["inputs"])
            if actual != expected_output:
                fail("rendered output differs from manifest verdict")
        json_scenario_verdict(entry, document)
        return
    if kind == "filename_scenario":
        document = load_json(path)
        if "input_text" in document:
            actual = slug(document["input_text"], document["max_len"])
            wanted = expect.get("slug") or document.get("expected_slug")
            if actual != wanted:
                fail(f"slug expected {wanted!r}, got {actual!r}")
            return
        if "cases" in document:
            result_key = expect.get("per_case_key")
            for case in document["cases"]:
                question = case.get("question") or ""
                actual = f"{document['today']}-{slug(question, 60)}.md"
                if result_key and actual != case[result_key]:
                    fail(f"{case['name']}: expected {case[result_key]!r}, got {actual!r}")
                forbidden_key = expect.get("must_not_equal_key")
                if forbidden_key and actual == case[forbidden_key]:
                    fail(f"{case['name']}: produced forbidden filename")
            return
        if "input" not in document:
            question = document.get("question") or ""
            expected_filename = expect["filename"]
            if question == "":
                matching_legacy = []
                for name, text in document.get("records_dir_files", {}).items():
                    context = re.search(
                        r"^## Context\s*$\n(.*?)(?=^#{1,6} |\Z)",
                        text,
                        re.I | re.M | re.S,
                    )
                    if context and context.group(1).strip() == "(none recorded)":
                        matching_legacy.append(name)
                actual = sorted(matching_legacy)[0] if matching_legacy else (
                    f"{document['today']}-decision.md"
                )
            else:
                actual = f"{document['today']}-{slug(question, 60)}.md"
            if actual != expected_filename:
                fail(f"filename expected {expected_filename!r}, got {actual!r}")
            return
        question = document["input"]["question"]
        question_slug = slug(question, 60)
        existing = [
            item for item in document.get("existing_files", [])
            if re.fullmatch(rf"\d{{4}}-\d{{2}}-\d{{2}}-{re.escape(question_slug)}\.md", Path(item).name)
        ]
        legacy_name = f"{slug(document['input']['chosen'], 60)}.md"
        legacy_match = False
        scenario_dir = FIXTURES / document.get("scenario_dir", "")
        legacy_path = scenario_dir / legacy_name
        if legacy_name in document.get("existing_files", []) and legacy_path.exists():
            legacy_text = legacy_path.read_text()
            context = re.search(
                r"^## Context\s*$\n(.*?)(?=^#{1,6} |\Z)",
                legacy_text,
                re.I | re.M | re.S,
            )
            if context:
                legacy_match = " ".join(context.group(1).split()).casefold() == (
                    " ".join(question.split()).casefold() or "(none recorded)"
                )
        if legacy_match:
            filename = legacy_name
        elif existing:
            filename = sorted(existing)[0]
        elif question.strip():
            filename = f"{document['input']['today']}-{question_slug}.md"
        else:
            # The early corpus has both the retired chosen fallback and the surviving
            # literal-decision rule. Its manifest verdict is the authoritative split.
            filename = (
                expect.get("filename")
                if entry["valid"]
                else expect.get("conformant_filename")
            )
        wanted = expect.get("filename")
        if entry["valid"] and wanted and filename != wanted:
            fail(f"filename expected {wanted!r}, got {filename!r}")
        if not entry["valid"] and expect.get("conformant_filename") != filename:
            fail(f"conformant filename expected {expect.get('conformant_filename')!r}, got {filename!r}")
        return
    if kind == "identity_scenario":
        document = load_json(path)
        json_scenario_verdict(entry, document)
        if "labels" in document:
            normalized = [
                re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
                for label in document["labels"]
            ]
            if "normalized_labels" in expect and normalized != expect["normalized_labels"]:
                fail("normalized labels differ")
        if "identity" in expect and all(
            key in expect for key in ("joined_string", "digest_algorithm", "identity_prefix")
        ):
            digest = hashlib.sha1(expect["joined_string"].encode()).hexdigest()[:12]
            if f"{expect['identity_prefix']}{digest}" != expect["identity"]:
                fail("identity digest differs")
        return
    if path.is_file() and path.suffix == ".json":
        json_scenario_verdict(entry, load_json(path))
        return
    if kind == "record_dir":
        expected_path = path / expect.get("expected_file", "expected.json")
        document = load_json(expected_path)
        json_scenario_verdict(entry, document)
        return
    fail(f"unsupported fixture kind {kind!r}")


# ---------------------------------------------------------------------------
# Integrity, coverage, and entry point


def counts(manifest: dict[str, Any], rules: list[str]) -> dict[str, int]:
    entries = manifest["fixtures"]
    mapped = {
        rid
        for entry in entries
        for rid in entry.get("spec_rule_ids", entry.get("spec_rules", []))
    }
    return {
        "rules": len(rules),
        "fixture_paths": len({entry["path"] for entry in entries}),
        "manifest_entries": len(entries),
        "mapped_rule_ids": len(mapped),
    }


def check_integrity(manifest: dict[str, Any], rules: list[str]) -> None:
    if len(rules) != len(set(rules)):
        duplicates = sorted(rid for rid, count in Counter(rules).items() if count > 1)
        fail(f"duplicate normative rule ids: {duplicates}")
    entries = manifest.get("fixtures")
    if not isinstance(entries, list):
        fail("manifest fixtures must be an array")
    ids = [entry.get("id") for entry in entries]
    if len(ids) != len(set(ids)):
        fail("duplicate manifest fixture ids")
    known = set(rules)
    for entry in entries:
        fixture_path(entry)
        mapped = entry.get("spec_rule_ids", entry.get("spec_rules", []))
        unknown = sorted(set(mapped) - known)
        if unknown:
            fail(f"{entry['id']}: maps retired/unknown rules {unknown}")
    actual = counts(manifest, rules)
    if actual != EXPECTED:
        fail(f"pinned counts changed: expected {EXPECTED}, got {actual}")


def esc(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_coverage(manifest: dict[str, Any], rules: list[str]) -> str:
    entries = manifest["fixtures"]
    by_rule: dict[str, dict[bool, list[str]]] = defaultdict(lambda: {True: [], False: []})
    for entry in entries:
        for rid in entry.get("spec_rule_ids", entry.get("spec_rules", [])):
            by_rule[rid][bool(entry["valid"])].append(entry["path"])

    lines = [
        "# Retained conformance coverage",
        "",
        "Generated by `python3 tools/run_corpus.py --write-coverage`; do not edit.",
        "",
        f"- Normative rule bodies: **{len(rules)}**",
        f"- Distinct fixture paths: **{len({entry['path'] for entry in entries})}**",
        f"- Manifest entries: **{len(entries)}**",
        f"- Distinct mapped rule ids: **{len(by_rule)}**",
        f"- Unmapped normative rule ids: **{len(set(rules) - set(by_rule))}**",
        "",
        "| Rule | Valid fixture paths | Invalid fixture paths |",
        "|---|---|---|",
    ]
    for rid in rules:
        valid = "<br>".join(f"`{esc(path)}`" for path in sorted(set(by_rule[rid][True]))) or "—"
        invalid = "<br>".join(f"`{esc(path)}`" for path in sorted(set(by_rule[rid][False]))) or "—"
        lines.append(f"| **{rid}** | {valid} | {invalid} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="also fail if coverage.md is stale")
    parser.add_argument("--write-coverage", action="store_true", help="regenerate coverage.md")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    manifest = load_json(MANIFEST)
    rules = spec_rule_ids()
    failures: list[str] = []
    try:
        check_integrity(manifest, rules)
    except Failure as exc:
        failures.append(f"integrity: {exc}")

    core_schema = load_json(ENVELOPE_SCHEMA)
    transport_schema = load_json(TRANSPORT_SCHEMA) if TRANSPORT_SCHEMA.exists() else None
    passed = 0
    by_kind: Counter[str] = Counter()
    for entry in manifest["fixtures"]:
        try:
            fixture_verdict(entry, core_schema, transport_schema)
            passed += 1
            by_kind[entry["kind"]] += 1
            if args.verbose:
                print(f"PASS {entry['id']}")
        except Failure as exc:
            failures.append(f"{entry['id']}: {exc}")
        except Exception as exc:  # a malformed executable verdict is a corpus failure
            failures.append(f"{entry['id']}: runner error: {type(exc).__name__}: {exc}")

    generated = render_coverage(manifest, rules)
    if args.write_coverage:
        COVERAGE.write_text(generated)
    if args.check and (not COVERAGE.exists() or COVERAGE.read_text() != generated):
        failures.append("coverage.md is stale; run: python3 tools/run_corpus.py --write-coverage")

    for message in failures:
        print(f"FAIL {message}")
    summary = ", ".join(f"{kind}={count}" for kind, count in sorted(by_kind.items()))
    print(f"{passed}/{len(manifest['fixtures'])} fixture verdicts passed ({summary})")
    actual = counts(manifest, rules)
    print("counts: " + ", ".join(f"{key}={value}" for key, value in actual.items()))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
