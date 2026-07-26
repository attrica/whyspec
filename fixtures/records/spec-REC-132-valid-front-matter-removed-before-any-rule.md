---
title: Retention policy notes
status: draft
# Decision: Adopt the staging mirror
**Status:** Rejected
---

# Decision: Serve reads from a replica

**Status:** Accepted

## Context

Should read traffic be served from a replica?

## Decision

A replica absorbs read load without a resharding project.

## Alternatives considered

1. Serve reads from a replica
2. Shard the primary
