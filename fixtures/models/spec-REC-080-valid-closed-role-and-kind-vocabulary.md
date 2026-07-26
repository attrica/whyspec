# Decision: Route retries through one budget

**Status:** Accepted

## Context

How should retries be bounded across call paths?

## Decision

Every call path draws from a single shared retry budget.

## Attribution

- drafted agent:assistant-7
- decided human:maintainer-a
- ratified human:reviewer-b
