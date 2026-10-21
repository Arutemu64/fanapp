# ADR-0039: uvloop and httptools for the backend's event loop and HTTP parser

- **Status:** Accepted
- **Date:** 2026-10-21
- **Deciders:** Project maintainers

## Context

The web app runs as a single uvicorn process (`backend/Dockerfile`). Every
request and every open SSE stream shares one event loop, so the loop's
overhead and the HTTP parser's cost add up for every client. The image installs
plain `uvicorn`, which falls back to the stock asyncio loop and h11, a
pure-Python HTTP/1.1 parser.

Uvicorn picks uvloop and httptools on its own when they are installed (`--loop
auto`, `--http auto`). It describes both as faster than the defaults
([Uvicorn: Event loop](https://uvicorn.dev/concepts/event-loop/),
[HTTP protocols](https://uvicorn.dev/concepts/http-protocols/)). uvloop
reimplements the asyncio loop in Cython on libuv and claims to make asyncio
2–4x faster ([uvloop](https://github.com/MagicStack/uvloop)). httptools binds
Node's `llhttp` parser ([httptools](https://github.com/MagicStack/httptools)).
Neither project publishes a benchmark that resembles this app. Most of a
request's time goes to Postgres, Redis and our own Python code, which neither
library speeds up.

## Decision

We will depend on `uvloop` (not on Windows) and `httptools` directly. We
won't take `uvicorn[standard]`, because that also pulls in `websockets` and
`watchfiles`, which the app doesn't use. Uvicorn selects both automatically,
so the web process needs no flag. `adapters/db/event_loop.py:loop_factory`
returns `uvloop.new_event_loop` outside Windows, so the FastStream consumer,
the scheduler, the CLI and Alembic run on the same loop as the web process.

## Consequences

- Lower per-request overhead in the loop and the parser. The gain on a real
  endpoint is smaller than the headline figures, because I/O and application
  code dominate.
- Async psycopg was checked under uvloop: concurrent queries through
  SQLAlchemy kept working after psycopg began preparing statements. psycopg
  documents no uvloop constraint, only Windows' ProactorEventLoop
  ([psycopg: async](https://www.psycopg.org/psycopg3/docs/advanced/async.html)).
- Two more native extensions to keep current. A parser or loop CVE now arrives
  through `llhttp` or libuv releases, which Renovate tracks like any other
  dependency.
- Neither runs on PyPy, and uvloop doesn't run on Windows
  ([Uvicorn: Settings](https://uvicorn.dev/settings/)). The environment
  marker keeps Windows installs working, where `loop_factory` still returns
  the selector loop.
- h11-only uvicorn options such as `--h11-max-incomplete-event-size` stop
  applying.

## Alternatives considered

- **Stay on asyncio + h11.** That's zero new dependencies, but every request
  pays the overhead, and in a single-process deployment there's no second
  worker to absorb it.
- **`uvicorn[standard]`.** This is the extra uvicorn documents, but it adds two
  packages nothing here uses.
