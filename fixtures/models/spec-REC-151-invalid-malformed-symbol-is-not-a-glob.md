# Decision: Validate requests at the edge

**Status:** Accepted

## Context

Where should request validation live?

## Decision

Request validation runs at the edge handler, before any service call.

## Governs

- src/edge/handler.py#
