# Decision: Keep the retry budget in one place

## Context

Where should retry limits be configured?

## Decision

One retry budget, read by every client. The predecessor record's header, kept here for the reader:

```markdown
# Decision: Per-client retry limits

**Status:** Rejected
```

The quoted record was retired by this one.
