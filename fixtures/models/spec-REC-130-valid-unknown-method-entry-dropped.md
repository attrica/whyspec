# Decision: Retry only idempotent calls

**Status:** Accepted

## Context

Which calls may the client retry?

## Decision

Only idempotent calls are retried.

## Evidence

- grep: retry call sites across the service
- benchmarked: the queue under sustained load
- read: the upstream client documentation
