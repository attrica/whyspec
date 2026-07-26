# Decision: Keep schema migrations forward-only

**Status:** Accepted

## Context

How should schema changes be rolled back?

## Decision

Migrations are forward-only; a rollback is written as a new migration.

## Attribution

- drafted agent:assistant-7
- decided human:maintainer-a
- ratified human:reviewer-b
