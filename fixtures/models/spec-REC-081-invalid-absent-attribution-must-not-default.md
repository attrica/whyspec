# Decision: Split the ingest worker in two

**Status:** Accepted

## Context

How should ingest be separated from enrichment?

## Decision

Ingest and enrichment run as two workers with a queue between them.
