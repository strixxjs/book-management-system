# 016. All book endpoints require authentication

## Decision
GET /books/, GET /books/{id}, and GET /books/export all require a
valid access token, same as write endpoints.

## Why
The spec mandates auth for create/update/delete. Reads are not
explicitly listed. We chose to require auth on all endpoints because
the book catalogue is treated as an internal resource — there is no
public-facing use case that justifies unauthenticated reads.

## Cost we accept
Stricter than the spec requires. A future decision to open reads
publicly is a one-line change (remove the dependency).