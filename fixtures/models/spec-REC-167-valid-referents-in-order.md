# Decision: Read the schema from one generated file

**Status:** Accepted
**Date:** 2026-05-13

## Context

Where does the generated schema view come from?

## Decision

One generator writes the schema view, and CI fails when the checked-in copy is stale.

## Validity

This stops applying when `tools/build_openapi.py` stops generating `schema/openapi.json`, or when
`schema/parsed-record.schema.json#properties` is no longer the source the generator reads. The
mechanism described in the rationale above names no artifact and declares no referent.
