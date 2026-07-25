# Decision: Keep the scheduler single-threaded

## Decision

The scheduler stays single-threaded.

## Alternatives considered

Work-stealing pools were discussed — promising, but unproven here.
Thread-per-task was rejected on memory grounds.
