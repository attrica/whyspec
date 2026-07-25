# DECISION: Adopt structured logging

## CONTEXT

Log lines were free-form and unparseable.

## DECISION

All services emit JSON log lines with a fixed key set.

## ALTERNATIVES CONSIDERED

1. Keep free-form logs.
2. Adopt structured logging.
