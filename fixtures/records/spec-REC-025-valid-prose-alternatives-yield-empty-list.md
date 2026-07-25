# Decision: Keep the scheduler single-threaded

## Decision

The scheduler stays single-threaded.

## Alternatives considered

We weighed a work-stealing pool and a thread-per-task model, but neither was written up as a formal option before the decision was taken.
