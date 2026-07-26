# Decision: Serve reads from a replica

**Status:** Accepted

## Context

Should read traffic be served from a replica?

## Decision

A replica absorbs read load without a resharding project.

## Alternatives considered

1. Shard the primary — rejected: the resharding window does not fit this quarter
2. Add a cache tier
