# Decision: Validate requests at the edge

**Status:** Accepted
**Date:** 2026-09-08
**Whyspec:** 0.2

## Context

Where should request validation live?

## Decision

Request validation runs at the edge handler, before any service call.
