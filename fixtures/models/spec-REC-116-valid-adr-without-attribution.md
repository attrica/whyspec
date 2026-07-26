# ADR-0044 - Serve reads from a replica

**Status:** Accepted

## Context

How should read load be shed from the primary?

## Decision

Read-only endpoints are served from a replica.
