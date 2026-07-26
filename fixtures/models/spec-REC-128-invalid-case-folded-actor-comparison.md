# Decision: Cap the export batch size

**Status:** Accepted

## Context

How large may one export batch be?

## Decision

A batch is capped at the size the reporting replica can absorb in one window.

## Attribution

- drafted human:Operator-A
- ratified human:operator-a
