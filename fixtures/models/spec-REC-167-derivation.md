# Decision: Publish the schema view from one generator

**Status:** Accepted
**Date:** 2026-05-16

## Context

How is the generated schema view kept from drifting?

## Decision

One generator writes the schema view and CI fails when the checked-in copy is stale.

## Validity

This stops applying when `tools/build_openapi.py` stops generating `schema/openapi.json`, when
`./tools/build_openapi.py` is replaced by hand-editing, or when the format described at
`https://spec.openapis.org/oas/v3.1.0` is no longer the one emitted.
