# 015. Structured Logging with structlog

## Status
Accepted

## Context
Without logging, there is no way to know which request caused a 500,
how long requests take, or whether the service is healthy.

## Decision
Use structlog with JSON output and a request-scoped request_id.

Every request gets a UUID assigned in middleware. The ID is bound to
structlog's context variables so it appears in every log line within
that request automatically. It is also returned in the X-Request-ID
response header so clients can report it.

One summary log line is written per request: method, path, status code,
duration in milliseconds.

## Consequences
Good:
- Every log line carries request_id — easy to trace a request across
  multiple log lines.
- JSON output works with any log aggregator without configuration.
- Request body and Authorization header are never logged — no data leakage.

Bad:
- structlog adds a dependency. The stdlib logging module would work too,
  but producing consistent JSON with it requires more boilerplate.
- No exception tracking service (Sentry). Acceptable for this scope —
  the unhandled exception handler logs type and message, which is enough
  to diagnose most failures from logs alone.