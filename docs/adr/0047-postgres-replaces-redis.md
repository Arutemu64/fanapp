# ADR-0047: PostgreSQL replaces Redis; drop the schedule cache and presence

- **Status:** Accepted
- **Date:** 2026-10-27
- **Deciders:** Project maintainers
- **Supersedes:** [ADR-0014](0014-cache-the-schedule-in-redis-with-etag.md) (the Redis cache; its removal of request-time timing stands)

## Context

A Valkey container held seven kinds of state: login sessions, email codes, the
attempt `RateLimiter`, the `Cooldown`, the ALTCHA replay guard, the rendered
schedule (ADR-0014) and the online-user count. The app serves about 200 users
and a schedule of about 200 entries. At that load Redis is one more service to
run, secure, back up and upgrade, for no speed anyone notices. It also ran
`maxmemory-policy allkeys-lru`, so it could evict sessions and rate-limit
counters under memory pressure.

NATS JetStream KV was the other candidate. A KV TTL is set only when a key is
created: a later put writes the value with no TTL, so the key stops expiring,
and changing a TTL means delete and create again
([NATS: TTL and limits](https://docs.nats.io/learn/key-value/ttl-and-limits)).
Sliding sessions would become a non-atomic delete and create. The KV docs show
no increment and no sorted sets, so the rate limiter would need workarounds.

## Decision

Keep the remaining state in PostgreSQL and remove the Redis service.

- **Four tables** (`adapters/db/models/expiring.py`): `auth_sessions`,
  `auth_codes`, `rate_limits` and `cooldowns`. Each row carries `expires_at`.
  Readers ignore rows past it, using the database clock. `PurgeExpiredState`
  deletes them on `SCHEDULER__EXPIRED_STATE_RETENTION_CRON`.
- **Own transactions.** The adapters (`adapters/db/expiring/`) run each call in
  a short transaction on the engine, outside the request's unit of work. A
  rate-limit hit must stick when the caller then raises and rolls back.
- **Atomicity from upserts.** `INSERT … ON CONFLICT DO UPDATE` replaces
  `INCR` and `SET NX`. The cooldown takes over a row only once its window has
  passed (`DO UPDATE … WHERE expires_at <= now()`), so of two concurrent claims
  exactly one gets a row back. `DELETE … RETURNING` replaces `GETDEL`.
- **Sessions are stored as SHA-256 hashes** of the cookie token, so a database
  dump or backup holds no live sessions
  ([OWASP Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)).
- **No foreign keys.** These rows are written on a connection separate from the
  request transaction that may have just inserted the referenced user. An FK
  check against an uncommitted row would wait on that transaction.
- **ALTCHA's replay guard is a `Cooldown` claim** lasting until the challenge
  expires.
- **Logged tables, not `UNLOGGED`.** An unlogged table is truncated after a
  crash ([PostgreSQL: CREATE TABLE](https://www.postgresql.org/docs/current/sql-createtable.html)),
  which would sign everyone out. The write-ahead-log savings don't matter at
  this volume.
- **No schedule cache.** `GetSchedule` reads and serializes on every request.
  The route still sends a strong `ETag` and answers `If-None-Match` with `304`,
  which saves bandwidth for clients on venue mobile data and keeps the offline
  warm-up cheap.
- **No presence.** The online-user count, `GET /users/online-count` and the
  organizer card that showed it are removed.

## Consequences

- One fewer service, password, volume and healthcheck. The state rides along
  in the existing Postgres backups.
- Deploying the migration signs everyone out once: Redis sessions are not
  copied.
- Each request that carries a session cookie checks out one more pool
  connection, briefly, to resolve it.
- A `schedule_updated` broadcast now sends every connected client to the
  database at once. ADR-0014 measured about 7 ms per uncached read of 200
  events, so 200 clients cost about 1.4 s of database time spread over the
  burst. That is acceptable at this scale. Revisit with a cache if the audience
  grows by an order of magnitude.
- Tests: these adapters commit outside the rolled-back test transaction, so an
  autouse fixture truncates the four tables between tests.

## Alternatives considered

- **NATS JetStream KV.** Rejected for the TTL and increment gaps above, and the
  NATS server already runs on a tight memory limit.
- **Keep Redis with `noeviction`.** This fixes the eviction risk but keeps the
  extra service, which was the cost being removed.
- **`UNLOGGED` tables.** Rejected: a crash would end every session.
