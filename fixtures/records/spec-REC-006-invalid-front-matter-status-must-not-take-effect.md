---
status: rejected
title: Move the log to network storage
---

# Decision: Keep the write-ahead log on local disk

## Context

Should the write-ahead log move to network storage?

## Decision

The log stays on local disk; network storage adds a failure domain.
