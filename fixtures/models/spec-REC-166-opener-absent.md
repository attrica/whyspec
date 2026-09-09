# Decision: Cache rendered pages at the edge

**Status:** Accepted
**Date:** 2026-05-12

## Context

Should rendered pages be cached at the edge?

## Decision

Rendered pages are cached at the edge for sixty seconds.

## Validity

Probably worth revisiting once `src/render/cache.py` grows a second eviction policy, but nobody
has committed to a condition yet.
