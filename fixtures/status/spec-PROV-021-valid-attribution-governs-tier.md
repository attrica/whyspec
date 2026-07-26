# ADR-0031: Pin the image base to a digest

**Status:** Accepted
**Date:** 2026-06-02

## Context

How do we make container builds reproducible?

## Decision

A digest pin makes a rebuild produce the same base layer as the build it reproduces.

## Alternatives considered

1. Pin the image base to a digest
2. Pin the image base to a moving tag

## Attribution

- drafted agent:build-assistant on 2026-06-02
- decided human:maintainer-a on 2026-06-02
- ratified human:reviewer-c on 2026-06-02
