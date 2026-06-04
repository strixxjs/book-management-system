# 007. Genre as VARCHAR + Pydantic validation, not a DB Enum

## Context
The spec wants genre restricted to a predefined list. The obvious move is a
Postgres ENUM so the DB enforces it. We didn't.

## Decision
genre is a plain VARCHAR(100) in the DB. The allowed list lives in the Pydantic
schema (Literal[...]), validated at the API boundary.

## Why
- Adding a genre to a Postgres ENUM means ALTER TYPE, which is awkward to change
  and doesn't play nicely inside transactions. The genre list is the kind of
  thing that changes — we don't want a type migration every time.
- The genre list is a business rule, not a data-integrity invariant. In our
  architecture, format gets validated by Pydantic. This is exactly that case.

## Cost we accept
- The DB will accept any string up to 100 chars. If something writes to the table
  outside the API (a manual psql, another service), a bad genre slips through.
  We're putting the validation line at the API, not the column.
- If the requirement were "nothing may ever write a bad genre", we'd use a CHECK
  constraint or ENUM. For a single API owning this table, the Pydantic list is
  the right balance.