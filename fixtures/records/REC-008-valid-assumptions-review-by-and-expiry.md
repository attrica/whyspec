# ADR-0054 — Back the search index with the vendor's hosted service

## Decision

Use the vendor's hosted search index rather than self-hosting.

## Assumptions

- The vendor's free tier stays available (review by 2026-12-01).
- Query volume stays under the vendor's rate limit (expires: traffic exceeds 50 req/s).
