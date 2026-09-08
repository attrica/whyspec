# Decision: Validate requests at the edge

**Status:** Accepted

## Context

Where should request validation live?

## Decision

Request validation runs at the edge handler.

## Why

A malformed request is cheapest to reject before it costs anything.
