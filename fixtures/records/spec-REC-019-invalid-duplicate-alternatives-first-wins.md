# Decision: Use one connection pool per process

## Decision

One pool per process, sized to the CPU count.

## Alternatives considered

1. One pool per process.
2. One pool per thread.
3. No pooling.

## Notes

A later editor appended a second Alternatives section by mistake.

## Alternatives considered

1. One pool per thread.
