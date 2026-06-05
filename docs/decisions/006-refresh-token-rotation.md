# 006. Refresh tokens stored in the DB, with rotation

## Context
Access tokens are short-lived (15 min). We need a way for a long-lived client
(a mobile app) to stay logged in without re-entering a password every hour —
but without a stolen token granting access forever.

## Decision
Access token: stateless JWT, 15 min, not stored anywhere.
Refresh token: 30 days, stored in a refresh_tokens table.
On every /refresh, the old token is deleted and a new one issued (rotation).

## Why
- A stateless token can't be revoked before it expires. We need to revoke:
  logout, rotation, reacting to abuse. A stateless refresh token with rotation
  is a contradiction.
- Rotation catches theft. If someone steals a refresh token and uses it, the
  real client's next refresh fails — its token is already gone. That's a signal
  something's wrong, not a silent 30-day breach.
- Delete + insert happen in one transaction (get_db commits at the end). If it
  fails halfway, everything rolls back. The user never ends up with no token.

## Cost we accept
- Refresh tokens are stored as plaintext JWT strings. If the database
  is read-compromised, tokens are usable until expiry. The production
  answer is to store only a SHA-256 hash and compare on lookup.
  Left as plaintext here to keep the implementation focused.