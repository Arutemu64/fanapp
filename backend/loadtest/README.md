# SSE load test

A scoped load test for the Server-Sent Events stream (`GET /events`), the most
load-sensitive part of the backend: every connected attendee holds one
long-lived stream open, and one admin action (a schedule edit, a settings
change) fans out to all of them at once.

It is **not** a generic "hammer the API" suite. It targets the three things that
actually bend under a convention-day crowd:

1. **Connection establishment** — how many concurrent `/events` streams open,
   and the handshake latency as N climbs.
2. **Heartbeat liveness** — every idle stream must get a named `ping` within
   `HEARTBEAT_INTERVAL_SECONDS` (15s, `presentation/web/routes/sse.py`).
3. **Broadcast fan-out** — how long a single broadcast takes to reach every
   held stream.

## Why not vanilla Locust

Locust's `HttpUser` model counts request/response transactions and recycles
tasks between them. SSE is the opposite: one request that never ends. Holding
thousands of open streams fights that model, and you end up writing a custom
streaming `User` with `stream=True` + `iter_lines` either way — at which point
Locust's process-per-core worker pool is just overhead for what a single asyncio
event loop does natively. The harness here (`sse_soak.py`) is that asyncio
client. It also mirrors how the backend itself serves SSE — one uvicorn worker,
one event loop (`docker-compose.yml` runs `uvicorn` with no `--workers`).

If you specifically want the Locust web UI or distributed multi-box load
generation, wrap the same logic in a `User` subclass whose task opens
`self.client.get("/events", stream=True)` and iterates `iter_lines()`, firing
`environment.events.request` per received event. The bottleneck this test
found (backend memory, below) is reproduced faster and more cheaply by the
asyncio runner, so start there.

## What it does

- Opens N **anonymous** SSE streams. `GET /events` needs no auth (an anonymous
  connection still subscribes to `sse.broadcast.*`), so the test isolates the
  SSE machinery from the auth/voting path — no seeded tickets or logins needed.
- Holds them open, recording the handshake event and every `ping`.
- Publishes one `schedule_updated` broadcast **straight to NATS** (subject
  `sse.broadcast.schedule_updated`), bypassing the auth-gated admin action that
  would normally emit it, and measures per-stream delivery latency.

Nothing here writes to Postgres.

## Running it

Bring up the backing services and the API (see the repo README / `justfile`):

```sh
just run-infra          # Postgres, Redis, NATS
just backend-migrate    # once, if the DB is fresh
just backend-dev        # API on http://127.0.0.1:8000
```

The broadcast step authenticates to NATS with the same env vars the app uses.
Export them from your `.env` before running:

```sh
export $(grep -E '^NATS__(USER|PASSWORD)=' ../.env | xargs)   # from backend/
```

Then, from `backend/`:

```sh
# 1x expected peak (500), realistic 50 conn/s ramp
uv run python loadtest/sse_soak.py -n 500 --ramp 10

# 2x peak (1000)
uv run python loadtest/sse_soak.py -n 1000 --ramp 20

# soak only, no fan-out measurement
uv run python loadtest/sse_soak.py -n 500 --ramp 10 --no-broadcast
```

Flags: `-n` connections, `--ramp` seconds to spread the opens over (0 = all at
once — a synchronised thundering-open, far harsher than real browsers, useful
for stress but not for steady-state latency), `--hold` seconds to hold before
the broadcast (keep ≥16 to observe at least one 15s heartbeat), `--base-url`,
`--nats-url`.

### Watching the ceiling

The binding constraint is the API worker's memory, so sample its RSS during the
run. The worker is the `multiprocessing`-fork child of `fanfan.main.web` (the
host entrypoint spawns it), not the launcher:

```sh
# find the worker pid (the fork child, highest RSS)
pgrep -f multiprocessing-fork
watch -n0.5 "ps -o rss= -p <pid> | awk '{print \$1/1024 \" MB\"}'"
```

In production this worker is capped at **256 MB** (`docker-compose.yml`,
`api.deploy.resources.limits`).

## What we measured (baseline, Sep 2026)

Run on the host (4 cores, no memory cap) against `just backend-dev`, so latency
is a floor and the **per-connection memory cost is the portable number** — the
production container is capped tighter and single-core.

| N | established | handshake p50 / p95 | fan-out p50 / p95 | worker RSS | Δ vs idle |
| --- | --- | --- | --- | --- | --- |
| 500 (1× peak) | 500/500 | 0.19s / 0.28s | 0.42s / 0.45s | 407 MB | +100 MB |
| 1000 (2× peak) | 1000/1000 | 0.21s / 0.60s | 0.99s / 1.09s | 505 MB | +198 MB |

Idle worker RSS: **307 MB** (host, dev deps). Every stream received its
heartbeat; zero errors; no file-descriptor wall at 1000.

**Cost per connection: ~200 KB, dead linear.** Latency, CPU and NATS fan-out are
*not* the bottleneck at these scales — memory is the only wall. Against the
256 MB production cap, that per-connection cost is what decides the ceiling: see
the audit notes in the PR / issue for the headroom math and the fixes
(raise the cap, halve the per-connection cost by collapsing the double
queue+task in `_stream_with_heartbeat`, add workers on a bigger host, and shed
with `uvicorn --limit-concurrency` before OOM).
