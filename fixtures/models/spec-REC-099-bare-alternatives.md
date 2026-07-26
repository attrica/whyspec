# Decision: Run our own broker

**Status:** Accepted

## Context

How should the service move work between stages?

## Decision

The service runs its own broker.

## Alternatives considered

1. Use a managed queue — the operator handles upgrades
2. Call the next stage directly
