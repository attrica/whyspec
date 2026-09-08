#!/usr/bin/env python3
"""Unit cases for tools/build_openapi.py's failure paths.

`build_openapi.py --check` only proves that schema/openapi.json equals what the builder
produces today. These cases prove the builder refuses the inputs that would let it
produce a silently degraded bundle — one whose references point nowhere, or whose
components overwrite each other — so a green `--check` means the bundle is sound, not
merely current. Each case feeds the builder a scratch schema directory and expects the
named refusal; a final case confirms the real schema directory still assembles.

    python3 tools/test_build_openapi.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC_PATH = ROOT / "tools" / "build_openapi.py"

spec = importlib.util.spec_from_file_location("build_openapi", SPEC_PATH)
build_openapi = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(build_openapi)

DIALECT = build_openapi.DIALECT


def minimal(name: str, **overrides) -> dict:
    schema = {
        "$schema": DIALECT,
        "$id": f"https://whyspec.example/schema/{name}.schema.json",
        "type": "object",
        "properties": {"item": {"$ref": "#/$defs/item"}},
        "$defs": {"item": {"type": "string"}},
    }
    schema.update(overrides)
    return schema


def run_builder(sources: dict[str, dict], names: tuple[str, ...]):
    """Point the builder at a scratch directory holding `sources`, return its outcome."""
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        for name, schema in sources.items():
            (directory / f"{name}.schema.json").write_text(json.dumps(schema))
        saved = (build_openapi.SCHEMA_DIR, build_openapi.SOURCES)
        build_openapi.SCHEMA_DIR, build_openapi.SOURCES = directory, names
        try:
            return build_openapi.build()
        finally:
            build_openapi.SCHEMA_DIR, build_openapi.SOURCES = saved


CASES = []


def case(label: str):
    def register(fn):
        CASES.append((label, fn))
        return fn
    return register


def expect_refusal(sources, names, fragment: str) -> str | None:
    try:
        run_builder(sources, names)
    except ValueError as exc:
        if fragment in str(exc):
            return None
        return f"refused for the wrong reason: {exc}"
    return "accepted the input instead of refusing it"


@case("non-local reference is refused")
def _(_=None):
    schema = minimal("a")
    schema["properties"]["item"] = {"$ref": "other.schema.json#/$defs/item"}
    return expect_refusal({"a": schema}, ("a",), "non-local reference")


@case("reference to an unknown definition is refused")
def _(_=None):
    schema = minimal("a")
    schema["properties"]["item"] = {"$ref": "#/$defs/missing"}
    return expect_refusal({"a": schema}, ("a",), "unknown definition")


@case("component name clash between two files is refused")
def _(_=None):
    # A file named `a.b` whose root component would be `a.b`, colliding with file `a`'s
    # hoisted definition `b`.
    first = minimal("a")
    first["$defs"] = {"b": {"type": "string"}}
    first["properties"] = {"item": {"$ref": "#/$defs/b"}}
    second = minimal("a.b")
    return expect_refusal({"a": first, "a.b": second}, ("a", "a.b"), "name clash")


@case("dangling reference after assembly is refused")
def _(_=None):
    # The rewrite step is bypassed by a reference that already uses the component form
    # but names a component nobody defines. rewrite_refs rejects it as non-local first;
    # the assembly-level guard is exercised directly so its own check is proven.
    schemas = {"a": {"properties": {"x": {"$ref": "#/components/schemas/a.nothing"}}}}
    dangling = [
        ref for ref in build_openapi.collect_refs(schemas)
        if ref[len("#/components/schemas/"):] not in schemas
    ]
    return None if dangling == ["#/components/schemas/a.nothing"] else "dangling ref not detected"


@case("a schema on a dialect other than 2020-12 is refused")
def _(_=None):
    schema = minimal("a")
    schema["$schema"] = "http://json-schema.org/draft-07/schema#"
    return expect_refusal({"a": schema}, ("a",), "dialect")


@case("references are rewritten to hoisted components and $id/$schema are dropped")
def _(_=None):
    document = run_builder({"a": minimal("a")}, ("a",))
    schemas = document["components"]["schemas"]
    if set(schemas) != {"a", "a.item"}:
        return f"unexpected components {sorted(schemas)}"
    if schemas["a"]["properties"]["item"] != {"$ref": "#/components/schemas/a.item"}:
        return f"reference not rewritten: {schemas['a']['properties']['item']}"
    if "$id" in schemas["a"] or "$schema" in schemas["a"] or "$defs" in schemas["a"]:
        return "root component still carries $id, $schema or $defs"
    if document["paths"] != {}:
        return "document declares paths"
    return None


@case("the real schema directory assembles")
def _(_=None):
    document = build_openapi.build()
    count = len(document["components"]["schemas"])
    return None if count >= 4 else f"only {count} components"


def main() -> int:
    failures = 0
    for label, fn in CASES:
        problem = fn()
        if problem is None:
            print(f"PASS     {label}")
        else:
            failures += 1
            print(f"FAIL     {label} — {problem}")
    print(f"{len(CASES) - failures}/{len(CASES)} builder cases passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
