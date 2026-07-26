# Decision: Retry only idempotent calls

**Status:** Accepted

## Context

Which calls may the client retry?

## Decision

Only idempotent calls are retried.

## Evidence

- grep: retry call sites across the service
- diff: the change against the previous release
- executed: the integration suite, once
- read: the upstream client documentation
- traced: one request through the gateway
