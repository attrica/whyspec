---
id: adrs-adr004
title: 'ADR004: Module Export Structure'
description: Architecture Decision Record on module export structure
---

## Context

Packages exported their internals inconsistently.

## Decision

Every package exports through a single index module.

## Consequences

Import paths become stable across refactors.
