# 002 — asyncpg as async PostgreSQL driver

## Context
FastAPI uses an async event loop. Database queries must not block it.

## Options
- psycopg2 — mature, sync only, blocks the event loop
- asyncpg — native async, fastest Python PostgreSQL driver
- psycopg3 — supports both sync and async, newer

## Decision
asyncpg via SQLAlchemy async extension (postgresql+asyncpg://).

## Rationale
asyncpg is the de-facto standard for async PostgreSQL in Python.
Excellent SQLAlchemy 2.0 support, actively maintained, battle-tested.
psycopg2 is incompatible with async FastAPI (blocks event loop).
psycopg3 is viable but less mature in the SQLAlchemy async ecosystem.