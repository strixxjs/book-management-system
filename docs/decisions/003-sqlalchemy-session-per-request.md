# 003 — SQLAlchemy session-per-request via FastAPI dependency

## Context
Need a strategy for managing database session lifecycle in async FastAPI.

## Options
- Global session — shared across all requests (race conditions, unusable)
- Session per request via dependency — one session per HTTP request
- Session per operation — new session for every query (no cross-operation transactions)

## Decision
Session per request using FastAPI dependency injection with yield.

## Rationale
Clean transaction boundary: one request = one unit of work.
Guaranteed cleanup via try/except/finally in the dependency.
Easily overridable in tests via app.dependency_overrides.
expire_on_commit=False prevents MissingGreenlet errors in async context.