# 005. Authors in their own table, not a text field on books

## Context
A book needs an author. Easiest option is an author_name column on books.
The spec asks for a normalized schema with books and authors.

## Decision
Separate authors table. books.author_id is a FK to authors.id,
with ON DELETE RESTRICT.

## Why
- A text field gives you "Tolkien", "J.R.R. Tolkien", and "tolkien" as three
  different authors. A FK keeps one author one row.
- "All books by this author" becomes a clean join instead of a fuzzy string match.
- RESTRICT (not CASCADE): you can't delete an author who still has books.
  That's enforced by the DB, not by service code someone might bypass.

## Cost we accept
- Creating a book is now two steps: find-or-create the author, then the book.
  This makes bulk import more interesting — that's where the race condition on
  concurrent author creation lives. We'll deal with it there.