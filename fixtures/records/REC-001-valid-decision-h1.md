# Decision: Store session tokens in the encrypted cookie

**Status:** Resolved
**Date:** 2026-06-01

## Context

Where should short-lived session tokens live: server-side session store or an
encrypted cookie on the client?

## Decision

Store them in an encrypted, signed cookie. No server-side session store to run
or scale.

## Alternatives considered

1. Server-side session store keyed by a session id cookie.
2. Encrypted cookie carrying the token directly.
