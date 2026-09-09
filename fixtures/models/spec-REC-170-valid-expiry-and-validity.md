# Decision: Pin the vendored parser to one minor version

**Status:** Accepted
**Date:** 2026-05-14

## Context

How tightly should the vendored parser be pinned?

## Decision

The vendored parser is pinned to one minor version and upgraded deliberately.

## Assumptions

- The upstream parser keeps its current release cadence (review by 2027-01-31) (expires: when upstream announces a rewrite)

## Validity

This stops applying when `vendor/parser/` is removed from the tree.
