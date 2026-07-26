# Decision: Bound the retry budget per call path

**Status:** Accepted

## Context

How should retries interact with earlier decisions?

## Decision

Each call path carries its own retry budget.

## Relations

- supersedes ADR-0007
- refines ADR-0012
- constrains dec-2b8c04
- motivated_by dec-7f3a91
- trade_off_against ADR-0019
- contradicts dec-5e1d77
