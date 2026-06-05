<div align="center">

# Book Management API

**Production-grade Book Management API — FastAPI · PostgreSQL · async SQLAlchemy 2.0**

<img src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white" alt="Python 3.12" />
<img src="https://img.shields.io/badge/FastAPI-async-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
<img src="https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white" alt="PostgreSQL 16" />
<img src="https://img.shields.io/badge/SQLAlchemy-2.0-D71F00?logo=sqlalchemy&logoColor=white" alt="SQLAlchemy 2.0" />
<img src="https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white" alt="Docker Compose" />
<a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff" /></a>
<img src="https://img.shields.io/badge/license-MIT-green" alt="License: MIT" />

</div>

---

A REST API for managing a book catalogue. The focus is on the decisions made *on top of* CRUD: where invariants are enforced, how concurrent writes are handled, the transaction semantics of bulk import, and the JWT token lifecycle. Every non-trivial choice is recorded as an ADR in [`docs/decisions/`](docs/decisions/).

## Quick start (Docker)

Requires Docker and Docker Compose. Nothing else.

```bash
cp .env.example .env          # defaults work for local evaluation as-is
docker compose up --build
```

On startup the `app` container runs `alembic upgrade head` (via `entrypoint.sh`) before launching the server, so the schema is always migrated — no manual step.

When it's up:

| What | URL |
| --- | --- |
| Health check (pings the DB) | http://localhost:8000/health |
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

## Configuration

All settings are read from `.env` via `pydantic-settings`. See `.env.example` for the full list.

| Variable | Default | Description |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+asyncpg://bookuser:bookpass@db:5432/bookdb` | Async DB URL. Uses the `db` Docker hostname. For host-side tools, point it at `localhost`. |
| `TEST_DATABASE_URL` | `postgresql+asyncpg://bookuser:bookpass@localhost:5432/bookdb_test` | Separate database used by the test suite. |
| `SECRET_KEY` | `change-me-in-production` | JWT signing key. Generate with `openssl rand -hex 32`. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access-token lifetime. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `30` | Refresh-token lifetime. |
| `DEBUG` | `false` | When `true`, SQLAlchemy echoes SQL. |

## API

All endpoints are under `/api/v1`. Interactive docs at `/docs`.

### Auth

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/auth/register` | Create a user (201). |
| `POST` | `/auth/login` | Returns `access_token` + `refresh_token`. |
| `POST` | `/auth/refresh` | Rotates the refresh token, returns a new pair. |
| `POST` | `/auth/logout` | Revokes the given refresh token (204). |

### Books — *all require a `Bearer` access token*

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/books/` | Create a book (201). |
| `GET` | `/books/` | List with filtering, pagination, sorting. |
| `GET` | `/books/{id}` | Retrieve one book. |
| `PATCH` | `/books/{id}` | Partial update. |
| `DELETE` | `/books/{id}` | Delete (204). |
| `POST` | `/books/import` | Bulk import from a `.json` or `.csv` file. |
| `GET` | `/books/export?format=json\|csv` | Export all books as a downloadable file. |

`GET /books/` query params: `title`, `author_name`, `genre`, `year_from`, `year_to`, `sort` (`title` / `year` / `created_at`), `limit` (1–100, default 20), `offset`.

**Auth flow:** `login` returns an access token (15 min) and a refresh token (30 days). Send the access token as `Authorization: Bearer <token>`. When it expires, `POST /auth/refresh` to get a fresh pair — the old refresh token is invalidated on use (rotation), so a mobile client stays logged in for 30 days without re-entering a password.

## Running the tests

The suite runs against a real PostgreSQL (no mocks), so it needs a separate test database. Create it once:

```bash
docker compose up -d db
docker compose exec db psql -U bookuser -d bookdb -c "CREATE DATABASE bookdb_test;"
```

Then run:

```bash
TEST_DATABASE_URL=postgresql+asyncpg://bookuser:bookpass@localhost:5432/bookdb_test \
uv run pytest
```

Each test runs inside a transaction that is rolled back on teardown, so tests are isolated and the database is left clean. See [ADR 011](docs/decisions/011-integration-tests-real-postgres.md).

## Local development (without Docker)

```bash
uv sync
export DATABASE_URL=postgresql+asyncpg://bookuser:bookpass@localhost:5432/bookdb
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
uv run ruff check .
```

## Architecture

A strict layered design — each layer has one responsibility, and routers never touch SQL.

```
HTTP
 └─ api/            routers, HTTP status codes, dependency wiring
     └─ schemas/    Pydantic: format invariants, (de)serialization
         └─ services/      business logic, orchestration, transaction boundaries
             └─ repositories/   the only layer that issues SQL
                 └─ models/     SQLAlchemy ORM models
core/   config, security (JWT, hashing), error handlers, structured logging, middleware
db/     async engine, session-per-request dependency
```

**Where invariants live:** *format* rules (non-empty title, year range, genre whitelist) are enforced in Pydantic at the boundary; *integrity* rules (uniqueness, foreign keys) in the database; *business* rules in the service layer. Full reasoning in [ADR 009](docs/decisions/009-validation-layer-placement.md).

## Design decisions

The spec asks for opinions on several questions. Short answers below; full reasoning in the linked ADRs.

- **Where are invariants enforced?** Format in Pydantic (cheapest rejection, before any DB round-trip), integrity in the DB. The year's upper bound is "current year", which moves yearly — a static `CHECK` can't express it, so it lives in the app. — [ADR 009](docs/decisions/009-validation-layer-placement.md)
- **Two requests create the same author at once?** `INSERT ... ON CONFLICT (name) DO UPDATE ... RETURNING` resolves the race in one atomic statement — no select-then-insert window, no duplicates. — [ADR 008](docs/decisions/008-author-identity-by-name.md), [ADR 010](docs/decisions/010-concurrent-author-creation.md)
- **A bulk import uploaded twice, or 99 valid + 1 broken?** All-or-nothing: every row is validated before any insert, and the first DB-level failure aborts the whole batch — the response is full success or `imported: 0` with a per-row error list. — [ADR 012](docs/decisions/012-bulk-import-strategy.md)
- **List behaviour at 10 000 rows?** Indexed columns (`author_id`, `genre`, `year`), deterministic sort with `id` as tiebreaker, bounded page sizes. Offset pagination; keyset is the next step if pages get deep. — [ADR 013](docs/decisions/013-export-selectinload.md)
- **How does an operator know it's healthy / which request caused a 500?** Every request gets a UUID `request_id`, bound to structured JSON logs and returned as `X-Request-Id`. `GET /health` pings the DB. — [ADR 015](docs/decisions/015-structured-logging.md)
- **Long-lived client auth?** Short access token + rotating refresh token, stored server-side so it can be revoked. — [ADR 006](docs/decisions/006-refresh-token-rotation.md)

### Deliberately out of scope

Named on purpose rather than half-built:

- **Keyset pagination** — offset is adequate for bounded admin-style listing; keyset is the answer at scale.
- **Hashing refresh tokens at rest** — stored as plaintext; production move is a SHA-256 hash. [ADR 006](docs/decisions/006-refresh-token-rotation.md).
- **Streaming / batched import & export** — both are in-memory; an async job is the answer for large ETL. [ADR 012](docs/decisions/012-bulk-import-strategy.md).
- **Refresh-token reuse → family revocation** — rotation fails the losing client, but a stolen token doesn't yet trigger a full session kill.
- **Rate limiting, error-tracking (Sentry)** — listed in the spec as optional.