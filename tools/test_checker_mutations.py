#!/usr/bin/env python3
"""Prove the retained checkers reject known classes of drift.

Each mutant receives an isolated copy of the repository. A mutant is *killed*
only when the named checker exits non-zero; notes and diagnostic wording are
irrelevant. The suite itself exits non-zero if any mutant survives.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Mutant:
    name: str
    mutate: Callable[[Path], None]
    command: tuple[str, ...]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    if text.count(old) != 1:
        raise RuntimeError(f"{path}: expected exactly one occurrence of {old!r}")
    path.write_text(text.replace(old, new, 1))


def change_json(path: Path, edit: Callable[[dict], None]) -> None:
    document = json.loads(path.read_text())
    edit(document)
    path.write_text(json.dumps(document, indent=2) + "\n")


def duplicate_rule(root: Path) -> None:
    path = root / "spec" / "whyfile-spec-draft.md"
    text = path.read_text()
    marker = "**[REC-001]**"
    insert = "\n\n**[REC-001]** Duplicate identifiers are forbidden.\n"
    path.write_text(text + insert)


def extra_closed_enum(root: Path) -> None:
    path = root / "schema" / "parsed-record.schema.json"
    change_json(
        path,
        lambda document: document["$defs"]["relation"]["properties"]["relation"]["enum"].append(
            "invented_relation"
        ),
    )


def extra_success_status(root: Path) -> None:
    path = root / "schema" / "envelope.schema.json"
    change_json(
        path,
        lambda document: document["$defs"]["why_ok"]["properties"]["status"]["enum"].append(
            "invented_success"
        ),
    )


def delete_named_property(root: Path) -> None:
    path = root / "schema" / "parsed-record.schema.json"
    change_json(path, lambda document: document["properties"].pop("assumptions"))


def shift_yields_column(root: Path) -> None:
    spec = root / "spec" / "whyfile-spec-draft.md"
    replace_once(
        spec,
        "| Heading | Required | Yields |\n"
        "|---|---|---|\n"
        "| `Decision` | **yes** | `rationale` — the section body, trimmed |",
        "| Heading | Required | Parser phase | Yields |\n"
        "|---|---|---|---|\n"
        "| `Decision` | **yes** | body | `rationale` — the section body, trimmed |",
    )
    text = spec.read_text()
    for start in (
        "| `Context` | no |",
        "| `Alternatives considered` *or* `Alternatives` | no |",
        "| `Recommendation` | no |",
        "| `Assumptions` | no |",
        "| `Status` | no |",
    ):
        text = text.replace(start, start + " body |", 1)
    spec.write_text(text)
    path = root / "schema" / "parsed-record.schema.json"
    change_json(path, lambda document: document["properties"].pop("recommendation"))


def remove_nested_required(root: Path) -> None:
    path = root / "schema" / "parsed-record.schema.json"

    def edit(document: dict) -> None:
        required = document["$defs"]["relation"]["required"]
        required.remove("provenance")

    change_json(path, edit)


def admit_foreign_variant(root: Path) -> None:
    path = root / "schema" / "envelope.schema.json"

    def edit(document: dict) -> None:
        document["$defs"]["why_ok"].pop("additionalProperties", None)

    change_json(path, edit)


def zero_row_extractor(root: Path) -> None:
    path = root / "spec" / "whyfile-spec-draft.md"
    replace_once(path, "| `command` | Status tokens |", "| Operation | Result vocabulary |")


def decrease_check_count(root: Path) -> None:
    path = root / "tools" / "check_schema.py"
    replace_once(
        path,
        "    check_tiers(spec, by_name, rep)\n",
        "    # mutant: check_tiers(spec, by_name, rep)\n",
    )


def dangling_rule_citation(root: Path) -> None:
    path = root / "schema" / "parsed-record.schema.json"

    def edit(document: dict) -> None:
        document["properties"]["question"]["x-rule"] = ["REC-999"]

    change_json(path, edit)


def stale_out_of_scope(root: Path) -> None:
    path = root / "tools" / "build_index.py"
    replace_once(
        path,
        '    "REC-070": "action",\n',
        '    "REC-070": "action", "REC-999": "action",\n',
    )


MUTANTS = (
    Mutant("duplicate_rule_identifier", duplicate_rule, ("tools/build_index.py", "--check")),
    Mutant("extra_closed_enum_member", extra_closed_enum, ("tools/check_schema.py",)),
    Mutant("extra_success_status_member", extra_success_status, ("tools/check_schema.py",)),
    Mutant("named_parsed_property_deleted", delete_named_property, ("tools/check_schema.py",)),
    Mutant("yields_column_shifted", shift_yields_column, ("tools/check_schema.py",)),
    Mutant("nested_required_entry_removed", remove_nested_required, ("tools/check_schema.py",)),
    Mutant("foreign_variant_key_admitted", admit_foreign_variant, ("tools/run_corpus.py",)),
    Mutant("extractor_harvests_zero_rows", zero_row_extractor, ("tools/check_schema.py",)),
    Mutant("total_check_count_decreases", decrease_check_count, ("tools/check_schema.py",)),
    Mutant("dangling_x_rule_citation", dangling_rule_citation, ("tools/check_schema.py",)),
    Mutant("stale_out_of_scope_entry", stale_out_of_scope, ("tools/build_index.py", "--check")),
)


def main() -> int:
    survivors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="whyfile-spec-mutants-") as temp:
        base = Path(temp)
        for number, mutant in enumerate(MUTANTS, 1):
            target = base / f"{number:02d}-{mutant.name}"
            shutil.copytree(
                ROOT,
                target,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            mutant.mutate(target)
            result = subprocess.run(
                (sys.executable, *mutant.command),
                cwd=target,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                print(f"SURVIVED {mutant.name}")
                survivors.append(mutant.name)
            else:
                diagnostic = (result.stdout + result.stderr).strip().splitlines()
                suffix = f" — {diagnostic[0]}" if diagnostic else ""
                print(f"KILLED   {mutant.name}{suffix}")
    print(f"{len(MUTANTS) - len(survivors)}/{len(MUTANTS)} mutants killed")
    return 1 if survivors else 0


if __name__ == "__main__":
    raise SystemExit(main())
