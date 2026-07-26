# Decision: Batch writes in the service

**Status:** Accepted

## Context

How should write throughput be raised?

## Decision

The service batches writes before they reach the database.

## Alternatives considered

1. Add a second queue — rejected: the on-call rota cannot absorb another broker
2. Batch writes on the client — deferred: revisit after the next capacity review
