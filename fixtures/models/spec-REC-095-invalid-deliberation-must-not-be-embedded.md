# Decision: Keep the write path single-threaded

**Status:** Accepted

## Context

How should concurrent writes be ordered?

## Decision

The write path stays single-threaded; ordering is a property callers rely on.

## Evidence

- read: the reviewer said a second writer would be cheaper, the author replied that the batch path already depends on ordering, the reviewer asked whether ordering could be restored downstream, the author said it could not without buffering the whole batch, and the reviewer then withdrew the objection
