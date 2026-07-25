# Decision: Use SQLite

**Status:** Resolved

## Context

Which embedded store backs the local index?

## Decision

Use SQLite: zero-ops, one file, good enough at this scale.

## Alternatives considered

1. SQLite.
2. Postgres running locally.

## Recommendation

Use SQLite
