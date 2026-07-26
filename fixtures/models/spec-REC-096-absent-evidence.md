# Decision: Keep the write path single-threaded

**Status:** Accepted

## Context

How should concurrent writes be ordered?

## Decision

The write path stays single-threaded; ordering is a property callers rely on.
