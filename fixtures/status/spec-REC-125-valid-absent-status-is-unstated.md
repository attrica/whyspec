# Decision: Cache rendered pages at the edge

**Date:** 2024-02-11

## Context

How do we cut render latency for anonymous readers?

## Decision

Edge caching removes the render step for pages that never vary per reader.

## Alternatives considered

1. Cache rendered pages at the edge
2. Precompute pages on write
