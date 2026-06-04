# 009. Format invariants live in Pydantic, integrity lives in the DB

## Context
The spec lists the rules a book must satisfy: non-empty title and author, year
between 1500 and the current year, genre from a fixed list. What it actually asks
is where each rule is enforced. Our architecture already says format is checked at
the API boundary and integrity in the DB, so the work is sorting each rule into
the right bucket.

## Decision
Format rules go in the Pydantic schemas, checked on the way in: title non-empty
after trimming, year in range, genre in the allowed set (a str Enum - 007 covers
why that set isn't a DB type). Integrity rules - uniqueness, foreign keys - stay
in the DB, where they hold for every row no matter what writes it.

The year upper bound is what fixes the line between the two. "At most the current
year" isn't a fixed number; it moves every January. A static CHECK constraint
can't express "now", so that rule has to be evaluated per request in the
application - there is nowhere else it can correctly live. Once that's clear the
rest sorts itself: anything dynamic or list-shaped is format and goes in Pydantic;
anything that must hold for every stored row forever is integrity and goes in the
schema.

## Why
- A bad title, year, or genre comes back as a 422 straight out of FastAPI, before
  any DB round-trip - the cheapest place to reject garbage.
- The year bound is computed at validation time, not frozen at process start, so a
  service booted in December still accepts next year's books in January. A test
  pins this: shift "now" forward and the boundary moves with it.
- Keeping format out of the DB means changing the genre list or the year floor is
  a code change, not a migration.

## Cost we accept
- Nothing below the API enforces these. A bulk SQL load or a second service could
  write a year of 1200 or a genre off the list. We accept that because the API is
  the only writer today; the moment that stops being true, the answer is a CHECK
  constraint as a second line of defence, not pulling the rule out of Pydantic.
  Same trade-off 007 makes for genre, stated once as a principle.