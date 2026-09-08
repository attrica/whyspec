# Decision: Consolidate retry budgets

**Status:** Accepted
**Date:** 2026-09-01

## Context

Where should retry limits be configured?

## Decision

One retry budget, read by every client.

## Alternatives considered

1. Per-client limits — rejected: drift between clients.

## Attribution

- drafted agent:reconstructor-2 on 2026-09-01
