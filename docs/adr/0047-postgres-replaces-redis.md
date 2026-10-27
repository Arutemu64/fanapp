# ADR-0047: PostgreSQL replaces Redis; drop the schedule cache and presence

- **Status:** Accepted
- **Date:** 2026-10-27
- **Deciders:** Project maintainers
- **Supersedes:** [ADR-0014](0014-cache-the-schedule-in-redis-with-etag.md) (the Redis cache; its removal of request-time timing stands)

## Context

A Valkey container held seven kinds of state: login sessions, email codes, the
attempt `RateLimiter`, the `Cooldown`, the ALTCHA replay guard, the rendered
schedule (ADR-0014) and the online-user count. The festival draws
about 1,000 attendees, so the app's ceiling is about that many users, and the
schedule holds about 200 entries. At that load every remaining operation is a
key lookup Postgres serves in well under a millisecond, and Redis is one more
service to run, secure, back up and upgrade, for no speed anyone notices. It also ran
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
  Readers ignore rows past it, using the database clock, so expiry never
  depends on cleanup. `PurgeExpiredState` deletes dead rows nightly
  (`SCHEDULER__EXPIRED_STATE_RETENTION_CRON`, on by default), as Django does
  for its database sessions
  ([Django: Clearing the session store](https://docs.djangoproject.com/en/5.2/topics/http/sessions/#clearing-the-session-store)).
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
- **`auth_sessions.user_id` references `users` with `ON DELETE CASCADE`**, as
  Lucia's reference schema does
  ([Lucia: PostgreSQL](https://v3.lucia-auth.com/database/postgresql)), so
  removing a user removes their sessions. Every flow creates a session after
  the user is committed. The other tables are keyed by emails, IPs or free-form
  keys and have nothing to reference.
- **The adapters run on their own small pool** (`ExpiringSessionFactory`,
  3 + 2 overflow connections) and open one short session per call. A login
  holds its unit-of-work connection while it creates a session. With one
  shared pool, a rush of logins could hold every connection while each waited
  for a second. A pool that no request waits on twice rules that out; HikariCP
  gives the minimum shared-pool size as `threads × (connections held − 1) + 1`,
  which an async server with no thread cap can't meet
  ([HikariCP: About Pool Sizing](https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing)).
  Each statement is a key lookup, and a 1-CPU database runs about two queries
  at once anyway
  ([PostgreSQL wiki: Number of Database Connections](https://wiki.postgresql.org/wiki/Number_Of_Database_Connections)).
  Tests bind the factory to the test's own connection with
  `join_transaction_mode="create_savepoint"`, SQLAlchemy's documented test
  recipe
  ([SQLAlchemy: Joining a Session into an External Transaction](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html#joining-a-session-into-an-external-transaction-such-as-for-test-suites)),
  so the writes see the test's uncommitted users and roll back with them.
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
- Each request that carries a session cookie checks out a connection from the
  small pool, briefly, to resolve it. Each process opens up to five more
  Postgres connections, which fits under `max_connections=60`.
- A `schedule_updated` broadcast now sends every connected client to the
  database at once. ADR-0014 measured about 7 ms per uncached read of 200
  events. At the 1,000-attendee ceiling, with perhaps 300–500 phones open, a
  burst costs 2–3.5 s of database time on the 1-CPU limit, so the slowest
  screens wait a few seconds. That is acceptable for a schedule change; a CPU
  bump is the first lever if it isn't.
- The adapters are request-scoped in DI because the test's connection is;
  that costs one small object per request.
- If the purge job stops, nothing breaks: expired rows are already ignored and
  the tables just grow slowly.

## Revisit when

Each signal points first at a cheaper fix than Redis.

- **Schedule bursts hurt.** `GET /schedule/` p95 stays above about a second
  after a `schedule_updated`, or the database sits at its CPU limit during
  bursts. Raise the CPU limit, then cache the rendered schedule in a Postgres
  row warmed by `PublishScheduleUpdated`. Redis only pays off once several API
  processes need one shared in-memory cache.
- **The small pool times out.** SQLAlchemy raises `QueuePool limit ... reached`
  for `ExpiringSessionFactory`. Raise `EXPIRING_POOL_SIZE` before anything else.
- **The expiring tables bloat.** Updates leave dead rows that `VACUUM`
  reclaims ([PostgreSQL: Routine Vacuuming](https://www.postgresql.org/docs/current/routine-vacuuming.html)).
  If `n_dead_tup` in `pg_stat_user_tables` for `rate_limits` or
  `auth_sessions` keeps outgrowing autovacuum, tune autovacuum for those
  tables; Redis is the answer only when the write rate is far past what a
  1,000-person event produces.
- **A feature needs per-heartbeat writes.** Presence, live counters or
  leaderboards updated every few seconds per user are what Redis is built for.
  Bring it back for that feature, not for the auth state here.

## Alternatives considered

- **NATS JetStream KV.** Rejected for the TTL and increment gaps above, and the
  NATS server already runs on a tight memory limit.
- **Keep Redis with `noeviction`.** This fixes the eviction risk but keeps the
  extra service, which was the cost being removed.
- **`UNLOGGED` tables.** Rejected: a crash would end every session.
