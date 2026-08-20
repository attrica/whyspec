#!/usr/bin/env python3
"""Regenerate the rule index (section 9.1) from the normative rule bodies.

The index is DERIVED, never maintained by hand. It went stale once — an index row
stated the exact inverse of its own rule body, and an implementer working from the
index would have built the opposite system. Generating it removes the failure mode
instead of asking people to remember.

    python3 tools/build_index.py           # rewrite the index in place
    python3 tools/build_index.py --check   # exit 1 if the index is stale (for CI)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SPEC = Path(__file__).resolve().parent.parent / "spec" / "whyspec-draft.md"
FAMILIES = ("REC", "PROV", "ENV", "VER")

# 9 excludes three classes from the conformance obligation and states that they are
# marked here. Generating the marks is what makes that sentence true rather than aspirational.
OUT_OF_SCOPE = {
    "VER-001": "governance", "VER-002": "governance", "VER-003": "governance",
    "VER-004": "governance", "VER-005": "governance",
    "VER-007": "governance", "VER-008": "governance",
    "ENV-008": "consumer", "ENV-009": "consumer", "ENV-038": "consumer",
    "ENV-039": "consumer",
    "REC-070": "action",
}
RULE_RE = re.compile(
    r"^\*\*\[((?:REC|PROV|ENV|VER)-\d{3})\]\*\*(.*?)(?=\n\n|\Z)",
    re.M | re.S,
)
ID_RE = re.compile(r"^\*\*\[((?:REC|PROV|ENV|VER)-\d{3})\]\*\*", re.M)
ROW_RE = re.compile(r"^\| ((?:REC|PROV|ENV|VER)-\d{3}) \| .*$", re.M)


LIMIT = 150

# A statement ending on a colon, or on a phrase that announces content to follow,
# has been cut before the thing it promises.
PROMISE_RE = re.compile(r"(:|following|these|below|as follows)\s*\.?\s*$", re.I)


def statement(body: str) -> str:
    """One table-cell line: as many whole sentences of the rule as fit.

    Whole sentences matter — a rule's second clause routinely carries the
    operative half ("the set is closed", "a body runs to the next heading"),
    and dropping it produced an index that was accurate but less useful than
    the prose it summarised. Truncation is the last resort and never splits a
    word.
    """
    text = " ".join(body.split())
    text = re.sub(r"\*\*|`|\[|\]", "", text)
    # sentence boundaries, ignoring the dot inside a version or decimal
    sentences = [s.strip() for s in re.split(r"(?<![0-9])\.(?:\s+|$)", text) if s.strip()]
    if not sentences:
        return ""

    out = sentences[0]
    for nxt in sentences[1:]:
        if len(out) + 2 + len(nxt) > LIMIT:
            break
        out = f"{out}. {nxt}"

    if len(out) > LIMIT:
        cut = out[:LIMIT].rsplit(" ", 1)[0]
        return cut.rstrip(" ,;:") + "…"

    # A rule whose substance is a list, table or code block continues AFTER a blank
    # line, which `RULE_RE` does not capture. Left alone the row reads "…both of the
    # following hold:" and carries nothing — a promise with no payload, in the one
    # table 9.1 presents as the complete list of rules. Say so explicitly rather
    # than trailing off, since a row that looks like a statement and isn't is worse
    # than a row that admits it is a pointer.
    if PROMISE_RE.search(out):
        return out.rstrip(". ") + " — see the rule body for the enumeration"
    return out.rstrip(".")


def build(text: str) -> dict[str, str]:
    matches = list(RULE_RE.finditer(text))
    ids = ID_RE.findall(text)
    duplicates = sorted({rid for rid in ids if ids.count(rid) > 1})
    if duplicates:
        raise ValueError(f"duplicate rule identifier(s): {duplicates}")
    return {match.group(1): statement(match.group(2)) for match in matches}


def render(text: str, rules: dict[str, str]) -> str:
    """Rewrite every index row, drop orphans, and insert rules that have no row yet.

    Insertion matters as much as rewriting: a rule added without a row is the same
    staleness in a different shape, and leaving it to be done by hand recreates the
    process that failed.
    """
    def repl(m: re.Match) -> str:
        rid = m.group(1)
        if rid not in rules:
            return ""
        mark = f" _(out of scope: {OUT_OF_SCOPE[rid]})_" if rid in OUT_OF_SCOPE else ""
        return f"| {rid} | {rules[rid]}.{mark} |"

    text = ROW_RE.sub(repl, text)
    text = re.sub(r"\n\n+(?=\| (?:REC|PROV|ENV|VER)-\d{3} \|)", "\n", text)

    for rid in sorted(set(rules) - set(ROW_RE.findall(text))):
        fam = rid.split("-")[0]
        rows = [r for r in ROW_RE.findall(text) if r.startswith(fam)]
        if not rows:                      # no table for this family yet
            continue
        anchor = max((r for r in rows if r < rid), default=rows[0])
        line = next(l for l in text.splitlines() if l.startswith(f"| {anchor} |"))
        mark = f" _(out of scope: {OUT_OF_SCOPE[rid]})_" if rid in OUT_OF_SCOPE else ""
        text = text.replace(line, f"{line}\n| {rid} | {rules[rid]}.{mark} |", 1)
    return text


def main() -> int:
    text = SPEC.read_text()
    try:
        rules = build(text)
    except ValueError as exc:
        print(f"rule index input is invalid: {exc}")
        return 1
    stale_scope = sorted(set(OUT_OF_SCOPE) - set(rules))
    if stale_scope:
        print(f"OUT_OF_SCOPE cites {len(stale_scope)} missing rule(s): {stale_scope}")
        return 1

    rebuilt = render(text, rules)
    still_missing = sorted(set(rules) - set(ROW_RE.findall(rebuilt)))
    if still_missing:
        print(f"could not place {len(still_missing)} rule(s): {still_missing[:5]} "
              f"— no index table exists for that family")
        return 1
    if "--check" in sys.argv:
        if rebuilt != text:
            stale = [rid for rid in rules
                     if f"| {rid} | {rules[rid]}. |" not in text]
            print(f"index is STALE for {len(stale)} rule(s): {stale[:8]}")
            print("run: python3 tools/build_index.py")
            return 1
        print(f"index consistent with {len(rules)} rule bodies")
        return 0

    SPEC.write_text(rebuilt)
    changed = sum(1 for rid in rules if f"| {rid} | {rules[rid]}. |" not in text)
    print(f"index regenerated from {len(rules)} rule bodies ({changed} row(s) were stale)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
