# Decision: Store session state in the database

## Context

Where should session state live?

## Decision

Sessions live in the primary database.

### Follow-up

Revisit if session volume exceeds the write budget.
