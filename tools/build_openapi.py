#!/usr/bin/env python3
"""Generate schema/openapi.json from the four JSON Schema files, or check it is current.

The schema files under schema/ are the single source of truth for the shapes the
specification defines (the parsed record, the recall envelope and the reserved command
variants, the transport envelope, the intent-layer objects). This script folds them into
one OpenAPI 3.1 document so that schema viewers (Redoc, Swagger UI, Stoplight, IDE
plugins) can render the shapes as navigable trees. Nothing in the output is written by
hand: `--check` regenerates and compares, the same discipline build_index.py applies to
the rule index, so the two views cannot drift.

The document defines NO endpoints (`paths` is empty). OpenAPI is used only for its
`components.schemas` container and the tooling around it; the specification itself does
not describe an HTTP surface.

How each source file becomes components:

  * the root schema becomes one component named after the file
    (`parsed-record`, `envelope`, `transport-envelope`, `intent-layer`);
  * each entry of the file's `$defs` becomes a component `<file>.<def>`;
  * every local reference `#/$defs/<def>` is rewritten to
    `#/components/schemas/<file>.<def>`;
  * `$schema` and `$id` are dropped from the components — the document-level
    `jsonSchemaDialect` states the dialect once, and a nested `$id` would change the
    base URI the rewritten references resolve against;
  * `x-` extension keywords (`x-rule`, `x-carries-intent`, ...) are kept verbatim,
    since OpenAPI permits them anywhere and they are how a shape cites its rule.

    python3 tools/build_openapi.py            # write schema/openapi.json
    python3 tools/build_openapi.py --check    # exit 1 if it is stale (for CI)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = ROOT / "schema"
SPEC = ROOT / "spec" / "whyspec-draft.md"
OUT = SCHEMA_DIR / "openapi.json"

# Order is the order the components appear in the document: the record first, then
# the envelope it is reported through, then the two profiles.
SOURCES = ("parsed-record", "envelope", "transport-envelope", "intent-layer")
DIALECT = "https://json-schema.org/draft/2020-12/schema"
LOCAL_REF = re.compile(r"^#/\$defs/([^/]+)$")
VERSION_RE = re.compile(r"^\*\*Version:\*\*\s*([0-9]+\.[0-9]+)", re.M)


def spec_version() -> str:
    match = VERSION_RE.search(SPEC.read_text())
    if not match:
        raise ValueError("spec header carries no '**Version:** N.N' line")
    return match.group(1)


def rewrite_refs(node, prefix: str, known: set[str]):
    """Return `node` with every local `$defs` reference pointed at its hoisted component."""
    if isinstance(node, dict):
        out = {}
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str):
                match = LOCAL_REF.match(value)
                if not match:
                    raise ValueError(f"{prefix}: non-local reference {value!r} is not supported")
                if match.group(1) not in known:
                    raise ValueError(f"{prefix}: reference to unknown definition {value!r}")
                out[key] = f"#/components/schemas/{prefix}.{match.group(1)}"
            else:
                out[key] = rewrite_refs(value, prefix, known)
        return out
    if isinstance(node, list):
        return [rewrite_refs(item, prefix, known) for item in node]
    return node


def components_from(name: str, schema: dict) -> dict:
    defs = schema.get("$defs", {})
    known = set(defs)
    root = {k: v for k, v in schema.items() if k not in ("$schema", "$id", "$defs")}
    if schema.get("$schema") != DIALECT:
        raise ValueError(f"{name}: dialect is {schema.get('$schema')!r}, expected {DIALECT!r}")
    components = {name: rewrite_refs(root, name, known)}
    for def_name, body in defs.items():
        components[f"{name}.{def_name}"] = rewrite_refs(body, name, known)
    return components


def build() -> dict:
    schemas: dict = {}
    for name in SOURCES:
        path = SCHEMA_DIR / f"{name}.schema.json"
        components = components_from(name, json.loads(path.read_text()))
        clash = set(components) & set(schemas)
        if clash:
            raise ValueError(f"component name clash: {sorted(clash)}")
        schemas.update(components)

    # Every reference in the assembled document must land on a component it contains.
    dangling = sorted(
        ref for ref in collect_refs(schemas)
        if not ref.startswith("#/components/schemas/")
        or ref[len("#/components/schemas/"):] not in schemas
    )
    if dangling:
        raise ValueError(f"dangling references after assembly: {dangling[:5]}")

    return {
        "openapi": "3.1.0",
        "jsonSchemaDialect": DIALECT,
        "info": {
            "title": "Whyspec shapes",
            "version": spec_version(),
            "summary": "The shapes the Whyspec specification defines, as schema components.",
            "description": (
                "Generated by tools/build_openapi.py from schema/*.schema.json; do not edit. "
                "This document defines no endpoints. It exists so that schema viewers can "
                "render the parsed record, the recall envelope (and the reserved command "
                "variants), the transport envelope and the intent-layer objects as "
                "navigable trees. The JSON Schema files remain the source of truth, and "
                "tools/check_schema.py keeps them consistent with the specification's prose."
            ),
            "license": {"name": "Apache-2.0", "identifier": "Apache-2.0"},
        },
        "paths": {},
        "components": {"schemas": schemas},
    }


def collect_refs(node, found=None) -> list[str]:
    if found is None:
        found = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str):
                found.append(value)
            else:
                collect_refs(value, found)
    elif isinstance(node, list):
        for item in node:
            collect_refs(item, found)
    return found


def render(document: dict) -> str:
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    try:
        rendered = render(build())
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"openapi input is invalid: {exc}")
        return 1
    count = len(json.loads(rendered)["components"]["schemas"])

    if "--check" in sys.argv:
        current = OUT.read_text() if OUT.exists() else ""
        if current != rendered:
            print(f"{OUT.relative_to(ROOT)} is STALE relative to schema/*.schema.json")
            print("run: python3 tools/build_openapi.py")
            return 1
        print(f"{OUT.relative_to(ROOT)} consistent with {count} components")
        return 0

    OUT.write_text(rendered)
    print(f"{OUT.relative_to(ROOT)} regenerated: {count} components from {len(SOURCES)} schema files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
