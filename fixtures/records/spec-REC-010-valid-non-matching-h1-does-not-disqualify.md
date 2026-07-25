# Engineering notes, week 14

Assorted notes from the weekly review.

# Decision: Serve reads from a replica

## Context

Read load saturated the primary.

## Decision

Read-only queries are routed to a replica.
