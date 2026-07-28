# Adopt a single retry budget

## Context

Retries were configured independently in four places.

## Decision

One retry budget is enforced at the client edge.

## Consequences

Per-call retry configuration is removed.
