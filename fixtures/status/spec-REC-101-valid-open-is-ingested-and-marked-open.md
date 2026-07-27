# Decision: Add a retry budget per caller

**Status:** Proposed
**Date:** 2026-04-14

## Context

How do we stop one caller from exhausting shared retries?

## Decision

A per-caller budget bounds the blast radius of a retry storm.

## Alternatives considered

1. Add a retry budget per caller
2. Add a single global retry budget
