# Decision: Use a shared cache layer

**Status:** Accepted
**Id:** dec-7f3a91
**Date:** 2026-03-04

## Context

How should read-heavy endpoints avoid repeating work?

## Decision

Reads go through a shared cache layer in front of the primary database.
