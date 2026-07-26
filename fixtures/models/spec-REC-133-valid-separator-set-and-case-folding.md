# Decision: Add a second queue

**Status:** Accepted

## Context

How should the write path shed load?

## Decision

A second queue absorbs the burst without changing the write path.

## Alternatives considered

1. Add a second queue — Rejected: the on-call rota cannot absorb another broker
2. Batch writes on the client – DEFERRED: revisit after the next capacity review
3. Cache read paths only - Partially-Adopted: taken for the report endpoints only
4. Move to a blue-green deploy pipeline
5. Keep the retry-deferred fallback path
