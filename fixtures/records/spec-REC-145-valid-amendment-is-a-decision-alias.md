# ADR-0007: Constitution amendment — validation at the edge

**Status:** Accepted

## Context

The constitution named no place for request validation.

## Amendment

Request validation runs at the edge handler, before any service call.

## Consequences

Services may assume validated input.
