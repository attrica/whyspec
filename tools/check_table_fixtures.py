#!/usr/bin/env python3
"""Check fixture expectations against sole-source normative tables.

The conformance runner checks implementations against fixtures, and
``check_schema.py`` checks prose field lists against schemas. This checker closes
the remaining pair: a fixture expectation must not contradict a table that the
spec declares to be the sole source for those values.

Tables are discovered from rule spans. Nothing below names REC-101 or restates
its rows. A table qualifies when its rule span contains a Markdown table and
either "sole ... source" or "this table governs".
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "spec" / "whyspec-draft.md"
MANIFEST = ROOT / "fixtures" / "manifest.json"

RULE_MARKER = re.compile(r"^\*\*\[((?:REC|PROV|ENV|VER)-\d{3})\]\*\*", re.M)
SOLE_SOURCE = re.compile(
    r"(?:sole\b.{0,40}\bsource|this table governs)",
    re.I | re.S,
)
TABLE_DIVIDER = re.compile(r"^:?-{3,}:?$")

# Increment only deliberately. A shrinking harvest is a checker failure.
EXPECTED_ASSERTIONS = 63

# A normative table can name its rows and values, but it cannot say where a
# fixture carries the input that selects a row. Keep that irreducible seam
# explicit. Everything after selection remains table-derived.
SELECTOR_REGISTRY: dict[str, tuple[str, ...]] = {
    "REC-101": ("status",),
}


def clean_markdown(value: str) -> str:
    return re.sub(r"[*_`]", "", value).strip()


def key_for(value: str) -> str:
    # Preserve semantic underscores already present in fixture keys while
    # discarding Markdown emphasis around table labels.
    cleaned = value.replace("*", "").replace("`", "").strip().strip("_")
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9_]+", "_", cleaned.casefold())).strip("_")


def cell_value(value: str) -> Any:
    """Convert a normative cell to the shape used by fixture expectations."""
    cleaned = clean_markdown(value)
    if cleaned.casefold() in {"—", "-", "n/a"}:
        return None
    if cleaned.casefold() == "yes":
        return True
    if cleaned.casefold() == "no":
        return False
    # Explanatory suffixes do not change the table token. For example,
    # "ground-truth intent, tier from record kind" is ``ground_truth_intent``.
    return key_for(cleaned.split(",", 1)[0])


@dataclass(frozen=True)
class NormativeTable:
    rule_id: str
    selector_field: str
    selector_paths: tuple[str, ...]
    fields: tuple[str, ...]
    rows: dict[str, dict[str, Any]]

    def select(self, value: Any) -> tuple[str, dict[str, Any]]:
        if value is None and "absent" in self.rows:
            return "absent", self.rows["absent"]
        selector = key_for(str(value))
        if selector in self.rows:
            return selector, self.rows[selector]
        if "any_other_value" in self.rows:
            return "any_other_value", self.rows["any_other_value"]
        raise KeyError(f"no row for selector {value!r}")


@dataclass(frozen=True)
class Observation:
    field: str
    value: Any
    selector: Any
    path: str
    role: str
    forbidden_group: str | None


class Report:
    def __init__(self) -> None:
        self.assertions = 0
        self.passed = 0
        self.failures: list[str] = []

    def check(self, condition: bool, message: str) -> None:
        self.assertions += 1
        if condition:
            self.passed += 1
        else:
            self.failures.append(message)


def rule_spans(text: str) -> Iterable[tuple[str, str]]:
    markers = list(RULE_MARKER.finditer(text))
    for index, marker in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(text)
        yield marker.group(1), text[marker.start():end]


def markdown_tables(span: str) -> Iterable[tuple[list[str], list[list[str]]]]:
    lines = span.splitlines()
    for index in range(len(lines) - 1):
        if not lines[index].lstrip().startswith("|"):
            continue
        divider = [
            cell.strip()
            for cell in lines[index + 1].strip().strip("|").split("|")
        ]
        if not divider or not all(TABLE_DIVIDER.fullmatch(cell) for cell in divider):
            continue
        headers = [
            cell.strip()
            for cell in lines[index].strip().strip("|").split("|")
        ]
        rows: list[list[str]] = []
        for line in lines[index + 2:]:
            if not line.lstrip().startswith("|"):
                break
            rows.append([cell.strip() for cell in line.strip().strip("|").split("|")])
        yield headers, rows


def discover_tables(text: str) -> list[NormativeTable]:
    tables: list[NormativeTable] = []
    for rule_id, span in rule_spans(text):
        if not SOLE_SOURCE.search(span):
            continue
        for headers, raw_rows in markdown_tables(span):
            fields = tuple(key_for(header) for header in headers)
            if len(fields) < 2:
                continue
            selector_field = fields[0]
            rows: dict[str, dict[str, Any]] = {}
            for raw_row in raw_rows:
                if len(raw_row) != len(fields):
                    raise ValueError(
                        f"{rule_id}: table row has {len(raw_row)} cells; "
                        f"header has {len(fields)}"
                    )
                selector = key_for(raw_row[0])
                if selector in rows:
                    raise ValueError(f"{rule_id}: duplicate table row {selector!r}")
                rows[selector] = {
                    field: cell_value(raw_row[column])
                    for column, field in enumerate(fields[1:], 1)
                }
            tables.append(
                NormativeTable(
                    rule_id=rule_id,
                    selector_field=selector_field,
                    selector_paths=SELECTOR_REGISTRY.get(rule_id, ()),
                    fields=fields[1:],
                    rows=rows,
                )
            )
    return tables


def observations(expect: dict[str, Any], table: NormativeTable) -> list[Observation]:
    found: list[Observation] = []
    row_names = set(table.rows)

    def walk(
        node: dict[str, Any],
        path: tuple[str, ...],
        inherited_selector: Any,
        inherited_role: str,
        inherited_forbidden_group: str | None,
    ) -> None:
        selector = inherited_selector
        for candidate in table.selector_paths:
            if candidate in node:
                selector = node[candidate]
                break
        if path and key_for(path[-1]) in row_names:
            selector = key_for(path[-1])

        for raw_key, value in node.items():
            key = key_for(raw_key)
            item_path = ".".join((*path, raw_key))
            role = inherited_role
            forbidden_group = inherited_forbidden_group
            field = key
            if key.endswith("_must_not_equal"):
                field = key.removesuffix("_must_not_equal")
                role = "must_not_equal"
                forbidden_group = item_path
            if field in table.fields and not isinstance(value, dict):
                found.append(
                    Observation(
                        field=field,
                        value=value,
                        selector=selector,
                        path=item_path,
                        role=role,
                        forbidden_group=forbidden_group,
                    )
                )
            if isinstance(value, dict):
                child_role = role
                if key.endswith("_must_not_equal"):
                    child_role = "counterexample"
                walk(
                    value,
                    (*path, raw_key),
                    selector,
                    child_role,
                    forbidden_group,
                )

    walk(expect, ("expect",), None, "expected", None)
    return found


def compare_fixture(
    entry: dict[str, Any],
    table: NormativeTable,
    report: Report,
) -> bool:
    found = observations(entry.get("expect", {}), table)
    if not found:
        return False

    resolved: list[tuple[Observation, Any, str]] = []
    for item in found:
        try:
            row_name, row = table.select(item.selector)
        except KeyError:
            report.check(
                False,
                f"{entry['id']}: {item.path} carries table column {item.field!r}, "
                f"but selector {item.selector!r} selects no {table.rule_id} row",
            )
            continue
        resolved.append((item, row[item.field], row_name))

    forbidden: dict[str, list[tuple[Observation, Any, str]]] = {}
    for item, wanted, row_name in resolved:
        if item.role == "expected":
            report.check(
                item.value == wanted,
                f"{entry['id']}: {item.field} expected {item.value!r}, "
                f"but {table.rule_id} row {row_name!r} requires {wanted!r}",
            )
        else:
            assert item.forbidden_group is not None
            forbidden.setdefault(item.forbidden_group, []).append(
                (item, wanted, row_name)
            )

    for group, items in forbidden.items():
        report.check(
            any(item.value != wanted for item, wanted, _row_name in items),
            f"{entry['id']}: {group} equals the conformant {table.rule_id} "
            "projection; counter-example is dead",
        )
    return True


def main() -> int:
    report = Report()
    try:
        tables = discover_tables(SPEC.read_text())
    except ValueError as error:
        print(f"FAIL {error}")
        return 1
    manifest = json.loads(MANIFEST.read_text())

    report.check(bool(tables), "no sole-source normative tables were discovered")
    print(
        "sole-source normative tables: "
        + (", ".join(table.rule_id for table in tables) if tables else "none")
    )

    for table in tables:
        report.check(
            bool(table.selector_paths),
            f"{table.rule_id}: sole-source table has no selector registry entry",
        )
        fixture_count = 0
        for entry in manifest["fixtures"]:
            mapped = entry.get("spec_rule_ids", entry.get("spec_rules", []))
            if table.rule_id not in mapped:
                continue
            fixture_count += compare_fixture(entry, table, report)
        report.check(
            fixture_count > 0,
            f"{table.rule_id}: no mapped fixture carried any table column keys",
        )

    if report.assertions != EXPECTED_ASSERTIONS:
        report.failures.append(
            "checker assertion count changed: "
            f"expected {EXPECTED_ASSERTIONS}, evaluated {report.assertions}"
        )

    for failure in report.failures:
        print(f"FAIL {failure}")
    print(
        f"{report.passed}/{report.assertions} table/fixture assertion(s) passed; "
        f"{len(report.failures)} failure(s)"
    )
    return 1 if report.failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
