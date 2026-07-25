# ADR-0022 - Pin the base image digest

## Context

Floating image tags produced irreproducible builds.

## Decision

Builds pin the base image by digest.

## Consequences

Upgrades become an explicit, reviewable change.

## References

Internal build runbook.

## Open questions

How often should digests be refreshed?
