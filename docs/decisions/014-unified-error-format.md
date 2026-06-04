# 014. Unified Error Response Format

## Status
Accepted

## Context
Without a consistent error format, clients face three different shapes
depending on where an error originates: FastAPI's built-in validation
response, our HTTPException detail strings, and raw 500 responses that
may leak implementation details.

## Decision
All errors return a single envelope:

    {"error": {"code": str, "message": str, "details": list | null}}

Three exception handlers registered in main.py cover every case:
- RequestValidationError → 422, code "validation_error", details per field
- HTTPException → status preserved, code derived from status integer
- Exception (catch-all) → 500, code "internal_error", no leak

## Consequences
Good:
- Clients need one error-handling path regardless of error origin.
- Stack traces never reach the client.
- Field-level validation errors are easy to map to form inputs.

Bad:
- The catch-all handler swallows the original exception without logging.
  This is acceptable now because observability (Step 11) will add
  structured logging. The handler has a comment marking the gap.

## Alternatives Considered
Leaving FastAPI's default format: rejected because the nested "loc"
array in validation responses is verbose and inconsistent with our
HTTPException strings.