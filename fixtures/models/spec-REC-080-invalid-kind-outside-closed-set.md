# Decision: Route retries through one budget

**Status:** Accepted

## Context

How should retries be bounded across call paths?

## Decision

Every call path draws from a single shared retry budget.

## Attribution

- drafted human:maintainer-a
- decided bot:assistant-7
