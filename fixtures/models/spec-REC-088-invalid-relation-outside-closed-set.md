# Decision: Bound the retry budget per call path

**Status:** Accepted

## Context

How should retries interact with earlier decisions?

## Decision

Each call path carries its own retry budget.

## Relations

- supersedes ADR-0007
- depends_on ADR-0012
