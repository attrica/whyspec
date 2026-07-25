# ADR-0045: Expose health checks on /healthz

## Decision

Add a `/healthz` endpoint that returns 200 once startup migrations complete.

## Consequences

The orchestrator can gate traffic on readiness instead of a fixed sleep.
