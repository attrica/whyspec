# Decision: Validate requests at the edge handler

**Status:** Accepted
**Date:** 2026-05-11

## Context

Where should request validation live?

## Decision

Request validation runs at the edge handler, before any service call.

## Validity

This stops applying when `src/edge/**/*.py` no longer routes through a single handler, or when
`src/edge/handler.py#validate_request` stops being the **only** entry point.
