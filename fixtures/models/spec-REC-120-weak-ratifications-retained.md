# Decision: Retry only idempotent calls

**Status:** Accepted

## Context

Which calls may the client retry?

## Decision

Only idempotent calls are retried; everything else fails fast.

## Attribution

- drafted agent:assistant-7
- decided human:maintainer-a
- ratified human:maintainer-a
- ratified human:reviewer-b
