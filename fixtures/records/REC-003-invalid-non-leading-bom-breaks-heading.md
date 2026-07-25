# ADR-0044 — Pin the lockfile in CI

﻿## Decision

CI installs from the committed lockfile only; it never resolves fresh versions.
