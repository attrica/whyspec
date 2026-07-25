# ADR-0050 — Use structured logging

**Status:** Accepted
**Date:** 2026-04-02

## Context

Free-text logs are hard to query in aggregate.

## Decision

Emit structured (JSON) log lines from every service.

## Consequences

Log aggregation queries become field lookups instead of regex.
