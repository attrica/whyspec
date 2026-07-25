# ADR-0042 — Use a shared cache layer

## Context

Two services independently re-fetch the same catalog data on every request.

## Decision

Introduce one shared cache layer that both services read through, invalidated on
catalog writes.

## Alternatives considered

1. Per-service caches. Rejected: the two caches would drift out of sync on writes.
2. No caching. Rejected: re-fetch cost dominates request latency at current traffic.

## Consequences

One dependency both services must be up for; latency improves for both.
