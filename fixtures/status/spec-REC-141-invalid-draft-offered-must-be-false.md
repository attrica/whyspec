# Decision: Route retries through one budget

**Status:** Draft

## Context

How should retries be bounded across call paths?

## Decision

A single shared budget is the simplest bound to reason about.
