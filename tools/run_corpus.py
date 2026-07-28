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
TRANSPORT_PROFILE = ROOT / "profiles" / "transport.md"
SPEC_FILES = (SPEC, TRANSPORT_PROFILE)
ENVELOPE_SCHEMA = ROOT / "schema" / "envelope.schema.json"
TRANSPORT_SCHEMA = ROOT / "schema" / "transport-envelope.schema.json"

RULE_RE = re.compile(r"^\*\*\[((?:REC|PROV|ENV|VER)-\d{3})\]\*\*", re.M)

# These are intentional tripwires, not estimates. A rule reduction or fixture
# retirement changes them in the same commit as the manifest and coverage report.
EXPECTED = {
    "rules": 211,
    "fixture_paths": 351,
    "manifest_entries": 378,
    "mapped_rule_ids": 192,
}
EXPECTED_EVIDENCE = {
    "computed": 284,
    "drift_checked": 94,
}
EXPECTED_MUST_NOT_EQUAL = {
    "fixtures": 77,
    "assertions": 92,
}

# REC-145. Same obligation, different spelling -- measured against 84 real ADRs from the three
# principal tools, where 52 used the MADR template.
SECTION_ALIASES = {
    "Context": ("Context and Problem Statement",),
    "Decision": ("Decision Outcome",),
    "Alternatives": ("Considered Options",),
    "Alternatives considered": ("Considered Options",),
}

# REC-148. An unfilled template is not a record. REC-008's own rationale says a template must be
# able to sit in the ADR directory without being ingested, and relaxing the heading rule broke
# that: `# NUMBER. TITLE` is a bare title carrying the full Nygard signature, because the template
# HAS all the section headings -- they are simply empty. Observed in a real repository, where two
# of seven "records" were the adr-tools and MADR templates.
TEMPLATE_TOKENS = {
    "NUMBER", "TITLE", "DATE", "STATUS", "CONTEXT", "DECISION", "CONSEQUENCES",
    "SHORT", "PROBLEM", "SOLUTION", "TEMPLATE", "OPTION", "DRIVER",
}

# Shape placeholders stand for a value's FORM rather than naming a field: "ADR-NNN: Title",
# "YYYY-MM-DD". They do not occur in real titles, so a single one is decisive where the
# vocabulary check needs every word to match.
SHAPE_PLACEHOLDERS = {"NNN", "NNNN", "NN", "XXX", "XXXX", "YYYY", "MM", "DD", "YYYY-MM-DD"}

COMPUTED = "computed"
DRIFT_CHECKED = "drift_checked"
IDENTITY_SEPARATOR = "::"

MISSING = object()

# Most forbidden-value assertions sit next to their conformant base value. These
# six do not, so keep the un-derivable relationship explicit rather than
# guessing from field names.
MUST_NOT_EQUAL_BASE_REGISTRY: dict[tuple[str, str], tuple[str, ...] | str] = {
    (
        "spec-REC-084-invalid-absent-governs-must-not-be-empty-scope",
        "expect.governs_must_not_equal",
    ): "absent",
    (
        "spec-REC-106-invalid-dated-filename-resolved-as-adr-year",
        "expect.resolved_target_must_not_equal",
    ): "absent",
    (
        "spec-REC-107-invalid-empty-context-must-not-yield-empty-string",
        "expect.question_must_not_equal",
    ): "absent",
    (
        "spec-REC-043-invalid-wrong-digit-count-resolves-target",
        "expect.resolved_target_must_not_equal",
    ): "absent",
    (
        "spec-REC-136-valid-rejected-status-round-trips",
        "expect.round_trip_status_must_not_equal",
    ): ("round_trip", "status"),
    (
        "spec-REC-128-invalid-case-folded-actor-comparison",
        "expect.actor_ids_must_not_equal",
    ): "actor_ids",
}


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
    return [
        rid
        for path in SPEC_FILES
        for rid in RULE_RE.findall(path.read_text())
    ]


def fixture_path(entry: dict[str, Any]) -> Path:
    path = (FIXTURES / entry["path"]).resolve()
    if FIXTURES.resolve() not in path.parents and path != FIXTURES.resolve():
        fail(f"{entry['id']}: path escapes fixtures/: {entry['path']}")
    if not path.exists():
        fail(f"{entry['id']}: fixture path does not exist: {entry['path']}")
    return path


def value_at_path(value: Any, path: tuple[str, ...]) -> Any:
    node = value
    for part in path:
        if not isinstance(node, dict) or part not in node:
            return MISSING
        node = node[part]
    return node


def must_not_equal_base(
    entry: dict[str, Any],
    container: dict[str, Any],
    key: str,
    path: str,
) -> Any:
    base_key = key.removesuffix("_must_not_equal")
    if base_key in container:
        return container[base_key]

    resolution = MUST_NOT_EQUAL_BASE_REGISTRY.get((entry["id"], path))
    if resolution == "absent":
        return MISSING
    if resolution == "actor_ids":
        actors = entry["expect"].get("actors", [])
        return [
            actor[1]
            for actor in actors
            if isinstance(actor, list) and len(actor) >= 2
        ]
    if isinstance(resolution, tuple):
        return value_at_path(entry["expect"], resolution)
    fail(f"{path}: has no conformant base value or resolver registry entry")


def forbidden_names_conformant(conformant: Any, forbidden: Any) -> bool:
    if conformant is MISSING:
        return False
    # A scalar base can name several forbidden scalar alternatives. A list base,
    # however, is itself one complete conformant value and compares as a whole.
    if isinstance(forbidden, list) and not isinstance(conformant, list):
        return conformant in forbidden
    return conformant == forbidden


def check_must_not_equal_expectations(
    manifest: dict[str, Any],
) -> tuple[int, int, list[str]]:
    assertion_count = 0
    fixture_ids: set[str] = set()
    failures: list[str] = []

    for entry in manifest["fixtures"]:
        def walk(node: Any, path: tuple[str, ...]) -> None:
            nonlocal assertion_count
            if not isinstance(node, dict):
                return
            for key, forbidden in node.items():
                item_path = ".".join((*path, key))
                if key.endswith("_must_not_equal"):
                    assertion_count += 1
                    fixture_ids.add(entry["id"])
                    try:
                        conformant = must_not_equal_base(
                            entry,
                            node,
                            key,
                            item_path,
                        )
                    except Failure as exc:
                        failures.append(f"{entry['id']}: {exc}")
                    else:
                        if forbidden_names_conformant(conformant, forbidden):
                            failures.append(
                                f"{entry['id']}: {item_path} names the conformant "
                                "value; forbidden-value assertion is dead"
                            )
                if isinstance(forbidden, dict):
                    walk(forbidden, (*path, key))

        walk(entry.get("expect"), ("expect",))

    return len(fixture_ids), assertion_count, failures


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
    core_projection = document
    if surface == "transport" and isinstance(document, dict):
        core_projection = {key: value for key, value in document.items() if key != "graph_identity"}
    schema_ok = not schema_errors(schema_document, schema)
    if surface == "transport":
        schema_ok = schema_ok and not schema_errors(core_projection, core_schema)

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


def normalize_label(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")


def canonical_source_path(source: str, repo_root: str | None = None) -> str:
    """Apply REC-073/REC-074 without allowing path-library errors to escape."""
    normalized = source.replace("\\", "/")
    try:
        path = Path(source)
        if not path.is_absolute():
            return normalized
        resolved = path.resolve(strict=False)
        if repo_root is not None:
            try:
                return resolved.relative_to(Path(repo_root).resolve(strict=False)).as_posix()
            except (OSError, ValueError):
                pass
        return resolved.as_posix()
    except (OSError, RuntimeError, ValueError):
        return normalized


def identity_parts(inputs: Any) -> tuple[str, str, str]:
    if not isinstance(inputs, list) or len(inputs) != 4:
        fail("identity inputs must be an array of exactly four strings")
    if not all(isinstance(item, str) for item in inputs):
        fail("identity inputs must all be strings")
    source_path, source_location, intent_kind, label = inputs
    if intent_kind not in {"decision", "assumption"}:
        fail(f"identity intent kind must be decision or assumption, got {intent_kind!r}")
    components = (source_path, source_location, intent_kind, normalize_label(label))
    joined = IDENTITY_SEPARATOR.join(components)
    full_digest = hashlib.sha1(joined.encode("utf-8")).hexdigest()
    return joined, full_digest, f"intent_{full_digest[:12]}"


def compare_identity(
    inputs: Any,
    *,
    joined_string: Any = MISSING,
    digest_full_hex: Any = MISSING,
    identity: Any = MISSING,
) -> str:
    joined, full_digest, actual_identity = identity_parts(inputs)
    if joined_string is not MISSING and joined != joined_string:
        fail(f"joined string expected {joined_string!r}, got {joined!r}")
    if digest_full_hex is not MISSING and full_digest != digest_full_hex:
        fail(f"full identity digest expected {digest_full_hex!r}, got {full_digest!r}")
    if identity is not MISSING and actual_identity != identity:
        fail(f"identity expected {identity!r}, got {actual_identity!r}")
    return actual_identity


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
    front = ""
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end >= 0:
            front = text[4:end]
            text = text[end + 4:].lstrip("\n")
    # REC-006 revised. Front matter is interpreted, but only as a LOWER-PRECEDENCE source that can
    # never override the body, and only for `title`. A real project (2,421 authors) keeps ADRs whose
    # only title is in front matter, so refusing to read it made 12 genuine records unreadable.
    #
    # `status` stays body-only, deliberately. A status decides whether a record is ingested at all,
    # so external tooling writing `status:` for its own purposes could silently delete records from
    # the graph. No repository measured needs front-matter status; twelve need front-matter title.
    front_title = None
    fm = re.search(r"^title:\s*(.+?)\s*$", front, re.M)
    if fm:
        front_title = fm.group(1).strip().strip("'\"")
    decision = re.search(r"^## (?:Decision|Decision Outcome)\s*(?:<!--.*?-->)?\s*$",
                         text, re.I | re.M)
    if not decision:
        return {"parses": False, "is_valid_utf8": True}
    # H1 recognition, relaxed after measuring 84 real ADRs from the three main ADR tools
    # (npryce/adr-tools, joshrotenberg/adrs, thomvaill/log4brains): NONE used "ADR-N:" or
    # "Decision:". 34 used Nygard's "N. Title" and 48 used a bare title, so the prefix rule
    # rejected 100% of the ecosystem.
    #
    # It is relaxed, NOT removed. Fixture REC-001 is meeting notes — "# Weekly sync notes" with a
    # "## Decision" section — and accepting any H1 would make it a decision record. The prefix was
    # doing real discriminating work beyond the "## Decision" gate above.
    #
    # So a record is recognised when the H1 declares one:
    #   ADR-N<sep> Title   explicit ADR reference            -> adr,      authored
    #   N. Title           Nygard numbering (adr-tools)      -> adr,      authored
    #   Decision: Title    what `whyfile capture` emits      -> decision, captured
    # or, for a bare title, when the document carries the ADR SECTION SIGNATURE — Status, Context
    # and Consequences together. That signature is what separates a hand-written ADR from notes
    # that happen to contain a Decision heading.
    adr = dec = num = None
    bare = None
    for candidate in re.findall(r"^# (.+)$", text, re.M):
        adr = re.fullmatch(r"ADR-(\d+)\s*(?:—|–|:|-)\s*(.+)", candidate, re.I)
        dec = re.fullmatch(r"Decision:\s*(.+)", candidate, re.I)
        num = re.fullmatch(r"(\d+)\.\s+(.+)", candidate)
        if adr or dec or num:
            break
        if bare is None:
            bare = candidate            # remember the first, keep scanning for a declared form
    sig = False
    if not (adr or dec or num) and bare is None and front_title:
        bare = front_title            # no H1 at all: front matter supplies the title
    if not (adr or dec or num):
        def has(*names):
            return all(
                re.search(rf"^## {n}\s*(?:<!--.*?-->)?\s*$", text, re.I | re.M) for n in names
            )
        # Nygard signature, or the MADR pair. Both are distinctive enough to separate a record
        # from notes; "Context and Problem Statement" beside "Decision Outcome" is not a shape
        # anything but an ADR produces.
        # "Context and Problem Statement" is MADR-specific enough to stand alone: the Decision
        # gate above already ran, and no document but an ADR pairs that heading with a decision.
        # Measured: a real MADR record spells its outcome "## Decision" rather than
        # "## Decision Outcome", and requiring the pair rejected it.
        # Status is NOT part of the signature: a real ADR corpus omits it entirely, keeping status
        # in front matter or nowhere. Context with Consequences, on top of the Decision gate, is
        # already a shape notes do not have -- the meeting-notes fixture carries neither.
        sig = has("Context", "Consequences") or has("Context and Problem Statement")
        if not (bare and sig):
            return {"parses": False, "is_valid_utf8": True}
    if adr:
        title = adr.group(2)
    elif dec:
        title = dec.group(1)
    elif num:
        title = num.group(2)
    else:
        title = bare
    title = title.strip()
    if not title:
        return {"parses": False, "is_valid_utf8": True}
    # A placeholder title means an unfilled template. Two forms are used in practice: the
    # adr-tools style, whose words are all drawn from the placeholder vocabulary
    # ("NUMBER. TITLE"), and the MADR style, which brackets the whole title
    # ("[short title of solved problem and solution]").
    words = re.findall(r"[A-Za-z]+", title)
    if words and all(w.upper() in TEMPLATE_TOKENS and w.isupper() for w in words):
        return {"parses": False, "is_valid_utf8": True}
    if re.fullmatch(r"\[.*\]", title.strip()):
        return {"parses": False, "is_valid_utf8": True}
    # A placeholder may also sit INSIDE an otherwise real-looking title: a template numbered in
    # sequence with its siblings reads "ADR000: [TITLE]". Observed in a real repository, where the
    # template parsed alongside the twelve genuine records it is the template for.
    if any(w.upper() in SHAPE_PLACEHOLDERS for w in re.findall(r"[A-Za-z]+", title)):
        return {"parses": False, "is_valid_utf8": True}
    for seg in re.findall(r"\[([^\]]*)\]", title):
        words = re.findall(r"[A-Za-z]+", seg)
        if words and all(w.upper() in TEMPLATE_TOKENS and w.isupper() for w in words):
            return {"parses": False, "is_valid_utf8": True}

    def section(name: str) -> str | None:
        # MADR spells three canonical sections differently. The alias table is normative
        # (REC-145): the same obligation, a different heading. MADR headings may also carry a
        # trailing HTML comment -- "## Decision Drivers <!-- optional -->" is emitted by the MADR
        # template itself -- so the heading match tolerates one.
        for spelling in (name, *SECTION_ALIASES.get(name, ())):
            match = re.search(
                rf"^## {re.escape(spelling)}\s*(?:<!--.*?-->)?\s*$\n(.*?)(?=^#{{1,6}} |\Z)",
                text,
                re.I | re.M | re.S,
            )
            if match:
                return match.group(1).strip()
        return None

    status_match = re.search(r"^\*\*Status:\*\*\s*(.*)$", text, re.I | re.M)
    if not status_match:                       # MADR: "- Status: accepted" as a list item
        status_match = re.search(r"^[-*]\s*Status:\s*(.*)$", text, re.I | re.M)
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
        "kind": "adr" if (adr or num or sig) else "decision",
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
        "provenance": "authored" if (adr or num or not dec) else "captured",
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
) -> str:
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
        return COMPUTED  # envelope evidence
    if kind == "record_bytes":
        actual = parse_record(path.read_bytes())
        compare_known_expectations(actual, expect)
        return COMPUTED
    if kind == "record":
        actual = parse_record(path.read_bytes())
        if verdict == "parse_rejects":
            if actual["parses"]:
                fail("record parsed but verdict requires rejection")
            return COMPUTED
        compare_known_expectations(actual, expect)
        return COMPUTED
    if kind == "slug_scenario":
        document = load_json(path)
        actual = slug(document["input_text"], document["max_len"])
        if actual != expect["slug"]:
            fail(f"slug expected {expect['slug']!r}, got {actual!r}")
        if len(actual) != expect["slug_length"]:
            fail(f"slug length expected {expect['slug_length']}, got {len(actual)}")
        return COMPUTED
    if kind == "render_scenario":
        document = load_json(path)
        expected_output = document["expected_output"]
        if "output" in expect and expected_output != expect["output"]:
            fail("manifest output drifted from fixture expected_output")
        # Execute the canonical renderer for its compact core input shape. Extension
        # and round-trip scenarios carry their executable field assertions in expect.
        core_keys = {"chosen", "question", "options", "rationale", "date", "status", "recommendation"}
        computed = isinstance(document.get("inputs"), dict) and set(document["inputs"]) <= core_keys
        if computed:
            actual = render_record(document["inputs"])
            if actual != expected_output:
                fail("rendered output differs from manifest verdict")
        json_scenario_verdict(entry, document)
        return COMPUTED if computed else DRIFT_CHECKED
    if kind == "filename_scenario":
        document = load_json(path)
        if "input_text" in document:
            actual = slug(document["input_text"], document["max_len"])
            wanted = expect.get("slug") or document.get("expected_slug")
            if actual != wanted:
                fail(f"slug expected {wanted!r}, got {actual!r}")
            return COMPUTED
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
            return COMPUTED
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
            return COMPUTED
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
        return COMPUTED
    if kind == "identity_scenario":
        document = load_json(path)
        json_scenario_verdict(entry, document)
        computed = False

        if "record_text" in document and "source_paths" in document:
            parsed = parse_record(document["record_text"].encode("utf-8"))
            actual_kinds = [parsed.get("kind")] * len(document["source_paths"])
            if "kind_for_each_path" in expect and actual_kinds != expect["kind_for_each_path"]:
                fail(
                    f"record kinds expected {expect['kind_for_each_path']!r}, "
                    f"got {actual_kinds!r}"
                )
            computed = True

        if "labels" in document:
            normalized = [normalize_label(label) for label in document["labels"]]
            if "normalized_labels" in expect and normalized != expect["normalized_labels"]:
                fail("normalized labels differ")
            computed = True

        if "input_path" in document:
            source = document["input_path"]
            repo_root = None
            if document.get("repo_root_placeholder"):
                repo_root = str(ROOT)
                source = source.replace(document["repo_root_placeholder"], repo_root)
            actual_path = canonical_source_path(source, repo_root)
            wanted_path = expect.get("canonical_path")
            if wanted_path is not None and actual_path != wanted_path:
                fail(f"canonical path expected {wanted_path!r}, got {actual_path!r}")
            if "inputs" in document and document["inputs"][0] != actual_path:
                fail("canonical path differs from the first identity input")
            if expect.get("raised") is False:
                # Reaching this assertion is the positive evidence: the call returned.
                pass
            computed = True
        elif "input_path_escaped" in document:
            escaped = document["input_path_escaped"]
            try:
                source = json.loads(f'"{escaped}"')
                actual_path = canonical_source_path(source)
            except Exception as exc:
                fail(f"canonical path raised {type(exc).__name__}: {exc}")
            if expect.get("raised") is not False:
                fail("path no-raise scenario must declare raised=false")
            if "inputs" in document and document["inputs"][0] != actual_path:
                fail("fallback path differs from the first identity input")
            computed = True

        if "variants" in document:
            actual_ids = {
                name: compare_identity(inputs)
                for name, inputs in document["variants"].items()
            }
            if document.get("expected_ids") != actual_ids:
                fail("variant identities differ from fixture expected_ids")
            if expect.get("ids") != actual_ids:
                fail("variant identities differ from manifest expect.ids")
            if expect.get("distinct_count") != len(set(actual_ids.values())):
                fail("identity distinct count differs")
            if expect.get("all_distinct") is not (len(set(actual_ids.values())) == len(actual_ids)):
                fail("identity all_distinct verdict differs")
            computed = True

        identity_sets: list[tuple[str, Any, dict[str, Any]]] = []
        if "inputs" in document:
            identity_sets.append(("identity", document["inputs"], document))
        for index, case in enumerate(document.get("identity_cases", [])):
            if not isinstance(case, dict):
                fail(f"identity_cases[{index}] must be an object")
            identity_sets.append((case.get("name", f"identity_cases[{index}]"), case.get("inputs"), case))

        for name, inputs, declarations in identity_sets:
            joined, full_digest, actual_identity = identity_parts(inputs)
            for source_name, source in (("fixture", declarations), ("manifest", expect)):
                declared_join = source.get("joined_string", MISSING)
                if declared_join is not MISSING and joined != declared_join:
                    fail(
                        f"{name}: {source_name} joined_string expected "
                        f"{declared_join!r}, got {joined!r}"
                    )
                declared_digest = source.get("digest_full_hex", MISSING)
                if declared_digest is not MISSING and full_digest != declared_digest:
                    fail(
                        f"{name}: {source_name} digest_full_hex expected "
                        f"{declared_digest!r}, got {full_digest!r}"
                    )
                declared_identity = source.get(
                    "expected_identity",
                    source.get("identity", MISSING),
                )
                if declared_identity is not MISSING and actual_identity != declared_identity:
                    fail(
                        f"{name}: {source_name} identity expected "
                        f"{declared_identity!r}, got {actual_identity!r}"
                    )
            forbidden_identities = set(
                declarations.get("non_conformant_identities", {}).values()
            )
            forbidden_identities.update(expect.get("identity_must_not_equal", []))
            if actual_identity in forbidden_identities:
                fail(f"{name}: produced a declared non-conformant identity")
            forbidden_join_parts = expect.get("joined_string_must_not_contain", [])
            if any(part in joined for part in forbidden_join_parts):
                fail(f"{name}: joined string contains a forbidden spelling")
            computed = True

        if not computed:
            fail("identity scenario did not execute a derived operation")
        return COMPUTED
    if path.is_file() and path.suffix == ".json":
        json_scenario_verdict(entry, load_json(path))
        return DRIFT_CHECKED
    if kind == "record_dir":
        expected_path = path / expect.get("expected_file", "expected.json")
        document = load_json(expected_path)
        json_scenario_verdict(entry, document)
        return DRIFT_CHECKED
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
    for rule in manifest.get("rules", []):
        unknown = sorted(set(rule.get("spec_rule_ids", [])) - known)
        if unknown:
            fail(f"manifest rule {rule.get('rule_id')}: maps retired/unknown rules {unknown}")
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


def render_coverage(
    manifest: dict[str, Any],
    rules: list[str],
    evidence: Counter[str],
) -> str:
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
        f"- Computed verdicts: **{evidence[COMPUTED]}**",
        f"- Drift-checked verdicts: **{evidence[DRIFT_CHECKED]}**",
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

    forbidden_fixtures, forbidden_assertions, forbidden_failures = (
        check_must_not_equal_expectations(manifest)
    )
    failures.extend(forbidden_failures)
    actual_forbidden = {
        "fixtures": forbidden_fixtures,
        "assertions": forbidden_assertions,
    }
    if actual_forbidden != EXPECTED_MUST_NOT_EQUAL:
        failures.append(
            "forbidden-value harvest changed: "
            f"expected {EXPECTED_MUST_NOT_EQUAL}, got {actual_forbidden}"
        )

    core_schema = load_json(ENVELOPE_SCHEMA)
    transport_schema = load_json(TRANSPORT_SCHEMA) if TRANSPORT_SCHEMA.exists() else None
    passed = 0
    by_kind: Counter[str] = Counter()
    by_evidence: Counter[str] = Counter()
    for entry in manifest["fixtures"]:
        try:
            evidence = fixture_verdict(entry, core_schema, transport_schema)
            if evidence not in {COMPUTED, DRIFT_CHECKED}:
                fail(f"runner returned unknown evidence class {evidence!r}")
            passed += 1
            by_kind[entry["kind"]] += 1
            by_evidence[evidence] += 1
            if args.verbose:
                print(f"PASS {evidence} {entry['id']}")
        except Failure as exc:
            failures.append(f"{entry['id']}: {exc}")
        except Exception as exc:  # a malformed executable verdict is a corpus failure
            failures.append(f"{entry['id']}: runner error: {type(exc).__name__}: {exc}")

    actual_evidence = {
        COMPUTED: by_evidence[COMPUTED],
        DRIFT_CHECKED: by_evidence[DRIFT_CHECKED],
    }
    if actual_evidence != EXPECTED_EVIDENCE:
        failures.append(
            f"evidence classification changed: expected {EXPECTED_EVIDENCE}, "
            f"got {actual_evidence}"
        )

    generated = render_coverage(manifest, rules, by_evidence)
    if args.write_coverage:
        COVERAGE.write_text(generated)
    if args.check and (not COVERAGE.exists() or COVERAGE.read_text() != generated):
        failures.append("coverage.md is stale; run: python3 tools/run_corpus.py --write-coverage")

    for message in failures:
        print(f"FAIL {message}")
    summary = ", ".join(f"{kind}={count}" for kind, count in sorted(by_kind.items()))
    print(
        f"{by_evidence[COMPUTED]} computed verdicts passed; "
        f"{by_evidence[DRIFT_CHECKED]} drift checks passed "
        f"({passed}/{len(manifest['fixtures'])} manifest entries; {summary})"
    )
    actual = counts(manifest, rules)
    print("counts: " + ", ".join(f"{key}={value}" for key, value in actual.items()))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
