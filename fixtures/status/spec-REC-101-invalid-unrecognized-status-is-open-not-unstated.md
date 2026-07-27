# Decision: Split the ingest worker pool

**Status:** Circulating with the platform group
**Date:** 2026-05-06

## Context

How do we keep slow ingest jobs from starving fast ones?

## Decision

Separate pools stop a long job from occupying every worker.

## Alternatives considered

1. Split the ingest worker pool
2. Add a per-job timeout
