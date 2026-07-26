# Decision: Keep the write path single-threaded

**Status:** Accepted

## Context

How should concurrent writes be ordered?

## Decision

The write path stays single-threaded; ordering is a property callers rely on.

## Evidence

- read: docs/notes/2026-03-04-write-path-review.md
- traced: one write through the service
