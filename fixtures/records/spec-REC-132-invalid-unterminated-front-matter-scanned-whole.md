---
title: Retention policy notes
status: draft

# Decision: Serve reads from a replica

**Status:** Rejected

## Context

Should read traffic be served from a replica?

## Decision

The lag budget cannot be met while the reporting workload shares the replica.

## Alternatives considered

1. Serve reads from a replica
2. Shard the primary
