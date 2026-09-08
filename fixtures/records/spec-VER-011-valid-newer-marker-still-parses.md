# Decision: Validate requests at the edge

**Status:** Accepted
**whyspec:** 9.4

## Context

Where should request validation live?

## Decision

Request validation runs at the edge handler, before any service call.
