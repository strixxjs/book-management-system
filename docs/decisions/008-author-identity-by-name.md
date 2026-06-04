# 008. Author identity is the author's name

## Context
Creating a book takes an author as a plain name string and either finds the
existing author or creates a new one - the two-step create flagged back in 005.
For that to be safe when two requests create the same author at the same time,
the DB needs one column it treats as the author's identity. Without it the two
requests either both insert and leave duplicate rows, or one hits an integrity
error nobody is handling.

## Decision
authors.name is unique. It's already enforced by a unique index (ix_authors_name)
from the initial migration, so there is nothing new to add - this ADR records why
that uniqueness is load-bearing. The name is the identity: case-sensitive, no
lower(name) normalization.

find-or-create leans on this directly. INSERT ... ON CONFLICT (name) infers its
arbiter from that unique index, so two concurrent inserts collapse to a single
row in one atomic statement instead of racing through a select-then-insert window.

## Why
- One author, one row - same reason as 005. A unique name is what makes that
  enforceable by the DB instead of hoped-for in service code.
- ON CONFLICT needs a unique index on the conflict target, and we already have
  exactly that on name. So the safe concurrent path costs nothing extra: no
  advisory locks, no read-modify-write gap.
- name is NOT NULL. Postgres treats NULLs as distinct under a unique index, so a
  nullable name would quietly let multiple NULL-named authors past the guarantee.

## Cost we accept
- Two real people who share a name become one row. For a book catalogue that's
  fine; disambiguating real authors (birth year, external IDs) is a far bigger
  modelling job than this assignment needs, and naming the simplification beats
  half-building it.
- Case-sensitive: "Orwell" and "orwell" are two authors. Case-insensitive identity
  would need a unique index on lower(name) or a CITEXT column with ON CONFLICT
  targeting that expression. Left case-sensitive on purpose.