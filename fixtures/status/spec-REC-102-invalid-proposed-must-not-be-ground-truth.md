# Decision: Move the session store off the primary

**Status:** Proposed
**Date:** 2026-04-09

## Context

Where should session state live?

## Decision

A dedicated store keeps session writes off the primary.

## Alternatives considered

1. Move the session store off the primary
2. Leave session state where it is
