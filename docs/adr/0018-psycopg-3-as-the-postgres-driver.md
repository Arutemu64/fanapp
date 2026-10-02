# ADR-0018: psycopg 3 as the PostgreSQL driver

- **Status:** Accepted
- **Date:** 2026-10-02
- **Deciders:** @arutemu64

## Context

The backend reached Postgres through asyncpg, both via SQLAlchemy's async engine
and directly for the outbox `LISTEN` connection
([ADR-0015](0015-listen-notify-wakes-the-outbox-relay.md)). By autumn 2026 asyncpg
had gone ten months without a release: 0.31.0 (November 2025) shipped regressions
that were fixed on master only in September 2026, and a
[maintenance-status issue](https://github.com/MagicStack/asyncpg/issues/1355)
was asking whether the project was still alive. It also stays at `0.x`, so a
minor release may break its API.

psycopg 3 releases steadily, ships type hints, and since SQLAlchemy 2.1
([release notes](https://www.sqlalchemy.org/blog/2026/09/24/sqlalchemy-2.1.0-released/))
is the default driver for `postgresql://` URLs. asyncpg is faster in raw driver
benchmarks, but behind the ORM the driver is a small share of request time.

## Decision

We will use psycopg 3 (`psycopg[binary]`) as the only Postgres driver, for the
SQLAlchemy engine and the outbox `LISTEN` connection alike.

- The engine sends the safety timeouts as libpq `options` (`-c name=value`) and
  pins the session `TimeZone` to UTC, so `timestamptz` values decode as UTC
  whatever the server's own setting. asyncpg did this on its own.
- `DatabaseConfig` forces the driver into a `DB__URL` DSN, so an existing
  `postgresql+asyncpg://` value keeps connecting.
- The `LISTEN` connection runs in autocommit and reads `notifies()` for a
  bounded interval between `SELECT 1` health probes.
- Every `asyncio.run` that may touch the database (and uvicorn) gets a selector
  loop on Windows, because psycopg's async mode cannot run on the default
  ProactorEventLoop.

## Consequences

- One maintained, typed driver; the `ty: ignore`s around asyncpg's untyped
  `connect()` are gone.
- Some raw-driver throughput is lost. That is acceptable at this scale; revisit
  only if profiling shows the driver on the hot path.
- `psycopg[binary]` bundles its own libpq, so libpq security fixes arrive through
  psycopg-binary releases (Renovate), not the base image. psycopg recommends a
  local `psycopg[c]` build for production, but that needs a compiler and
  `pg_config` in the image and on every Windows dev machine.
- Sentry has no psycopg 3 integration
  ([getsentry/sentry-python#2427](https://github.com/getsentry/sentry-python/issues/2427)).
  `SqlalchemyIntegration` still spans every pooled query; only the raw `LISTEN`
  connection goes untraced.

## Alternatives considered

- **Stay on asyncpg.** Faster and working in production, but it depends on a
  project whose release cadence had stalled, and it is not SQLAlchemy's default.
- **Keep asyncpg only for `LISTEN`.** Two drivers to keep patched for one
  connection; psycopg's `notifies()` covers the need.
