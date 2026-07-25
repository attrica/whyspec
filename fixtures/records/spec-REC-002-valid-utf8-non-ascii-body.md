# ADR-0014 — Route retries through one budget

## Context

Retries were configured per-caller, so a single slow dependency could multiply load.

## Decision

One shared retry budget, expressed in requests-per-second, is enforced at the client edge. Café-style naïve per-caller limits are removed.

## Alternatives considered

1. Per-caller retry caps — rejected: they compose badly.
2. No retries at all — rejected: transient faults become user-visible.
