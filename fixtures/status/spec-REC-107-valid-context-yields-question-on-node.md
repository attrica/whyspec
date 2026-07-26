# Decision: Ship schema changes ahead of the code that needs them

**Status:** Accepted
**Date:** 2026-05-12

## Context

How do we roll out a schema change without a coordinated deploy?

## Decision

An additive-first schema change lets old and new code run against the same tables.

## Alternatives considered

1. Ship schema changes ahead of the code that needs them
2. Deploy schema and code together behind a maintenance window
