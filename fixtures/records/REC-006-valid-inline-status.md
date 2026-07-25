# ADR-0046 — Serve the docs site from a CDN

**Status:** Accepted
**Date:** 2026-05-11

## Decision

Serve the static docs build from a CDN edge cache in front of the origin bucket.

## Alternatives considered

1. Serve directly from the origin bucket. Rejected: no edge caching, higher latency
   for distant readers.
