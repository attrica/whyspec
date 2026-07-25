# ADR-0044 — Pin the lockfile in CI

## Decision

CI installs from the committed lockfile only; it never resolves fresh versions.

## Alternatives considered

1. Let CI re-resolve dependencies on every run. Rejected: non-reproducible builds.
