# Adopt a single retry budget

## Status

Accepted

## Context and Problem Statement <!-- optional -->

Retries were configured independently in four places.

## Decision Outcome

One retry budget is enforced at the client edge.

## Consequences

Per-call retry configuration is removed.
