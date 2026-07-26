# Decision: Serve reads from a replica

**Status:** Accepted
**Date:** 2026-04-02

## Context

How do we shed read load?

## Decision

A replica absorbs read load without a resharding project.

## Alternatives considered

1. Serve reads from a replica
2. Shard the primary
