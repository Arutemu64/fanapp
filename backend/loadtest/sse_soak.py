"""SSE connection-soak + broadcast fan-out load test.

Why asyncio + httpx and not vanilla Locust: SSE is a long-lived, stateful
connection, not a request/response. Locust's User model counts requests and
recycles tasks; holding thousands of open streams fights that model and needs a
custom streaming User either way (see loadtest/README.md). A single asyncio
event loop holds N open streams cheaply and faithfully mirrors how the backend
itself serves them (one uvicorn worker, one loop — see docker-compose.yml).

What it exercises (the ceilings identified in the audit, README.md):
  1. Connection establishment — how many concurrent /events streams actually
     open, and the handshake latency distribution as N climbs. A reverse-proxy
     or file-descriptor cap shows up here as refused/hung connections.
  2. Heartbeat liveness — every idle stream must receive a named `ping` within
     HEARTBEAT_INTERVAL_SECONDS (15s, sse.py). Missing pings mean the single
     event loop is starved.
  3. Broadcast fan-out — publish one `sse.broadcast.schedule_updated` straight
     to NATS (bypassing the auth-gated admin action that would normally emit it)
     and measure how long every held stream takes to receive it.

The streams are anonymous: GET /events needs no auth (StreamEvents resolves an
anonymous user_id=None and still subscribes to sse.broadcast.*, see
stream_events.py), so the soak needs no seeded tickets or logins. That isolates
the SSE machinery from the voting/auth path on purpose.

Run: see loadtest/README.md. Nothing here writes to the database.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import time
from dataclasses import dataclass, field

import httpx
import nats


@dataclass(slots=True)
class ConnStats:
    """Per-connection outcome, aggregated into the run report."""

    connected: bool = False
    handshake_latency: float | None = None  # seconds from request to handshake event
    pings: int = 0
    broadcast_latency: float | None = None  # seconds from publish to receipt
    error: str | None = None


@dataclass(slots=True)
class Run:
    connections: int
    base_url: str
    nats_url: str
    hold_seconds: float
    stats: list[ConnStats] = field(default_factory=list)
    # Set to the wall-clock instant the broadcast is published, so each stream
    # can compute its own delivery latency against a single shared reference.
    broadcast_sent_at: float | None = None


def _parse_sse_block(block: str) -> tuple[str | None, str | None]:
    """Return (event, data) from one SSE record (fields separated by newlines)."""
    event: str | None = None
    data_lines: list[str] = []
    for line in block.splitlines():
        if line.startswith("event:"):
            event = line[len("event:") :].strip()
        elif line.startswith("data:"):
            data_lines.append(line[len("data:") :].strip())
    return event, "\n".join(data_lines) if data_lines else None


async def _run_stream(run: Run, index: int, ready: asyncio.Event) -> None:
    """Hold one SSE stream open, recording handshake, pings and the broadcast."""
    stat = ConnStats()
    run.stats[index] = stat
    started = time.perf_counter()
    # No total timeout: the stream is meant to stay open for the whole soak.
    timeout = httpx.Timeout(connect=30.0, read=None, write=30.0, pool=30.0)
    headers = {"Accept": "text/event-stream", "Cache-Control": "no-cache"}
    try:
        async with (
            httpx.AsyncClient(base_url=run.base_url, timeout=timeout) as client,
            client.stream("GET", "/events", headers=headers) as resp,
        ):
            if resp.status_code != httpx.codes.OK:
                stat.error = f"HTTP {resp.status_code}"
                ready.set()
                return
            stat.connected = True
            buffer = ""
            async for chunk in resp.aiter_text():
                buffer += chunk
                # SSE records are separated by a blank line.
                while "\n\n" in buffer:
                    block, buffer = buffer.split("\n\n", 1)
                    event, _ = _parse_sse_block(block)
                    now = time.perf_counter()
                    if event == "connection_established":
                        stat.handshake_latency = now - started
                        ready.set()
                    elif event == "ping":
                        stat.pings += 1
                    elif event == "schedule_updated":
                        if run.broadcast_sent_at is not None:
                            stat.broadcast_latency = (
                                time.perf_counter() - run.broadcast_sent_at
                            )
                        return
    except Exception as exc:  # noqa: BLE001 - report, never abort the whole run
        stat.error = f"{type(exc).__name__}: {exc}"
        ready.set()


async def _publish_broadcast(run: Run) -> None:
    """Publish one schedule_updated broadcast directly to NATS.

    Mirrors NatsRealtimeGateway.publish for a payload-less signal: subject
    sse.broadcast.<event_name>, body a JSON SSEMessage with an empty data dict.
    Credentials come from NATS__USER / NATS__PASSWORD, the same env vars the app
    reads (docker-compose.yml), so the harness needs no secret on its CLI.
    """
    nc = await nats.connect(
        run.nats_url,
        user=os.environ.get("NATS__USER"),
        password=os.environ.get("NATS__PASSWORD"),
        allow_reconnect=False,
    )
    try:
        payload = json.dumps({"event_name": "schedule_updated", "data": {}}).encode()
        run.broadcast_sent_at = time.perf_counter()
        await nc.publish("sse.broadcast.schedule_updated", payload)
        await nc.flush()
    finally:
        await nc.close()


def _pct(values: list[float], p: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    k = max(0, min(len(ordered) - 1, round((p / 100) * (len(ordered) - 1))))
    return ordered[k]


def _report(run: Run, wall: float) -> bool:
    stats = run.stats
    connected = [s for s in stats if s.connected]
    errored = [s for s in stats if s.error]
    handshakes = [s.handshake_latency for s in connected if s.handshake_latency]
    fanout = [s.broadcast_latency for s in connected if s.broadcast_latency is not None]
    no_ping = [s for s in connected if s.pings == 0]

    print("\n" + "=" * 60)
    print(f"SSE soak — target {run.connections} connections")
    print("=" * 60)
    print(f"  established:      {len(connected)}/{run.connections}")
    print(f"  errored:          {len(errored)}")
    if errored:
        # Collapse identical errors so one cap (e.g. a refused-connection wall)
        # reads as a count, not a wall of duplicate lines.
        kinds: dict[str, int] = {}
        for s in errored:
            kinds[s.error or "?"] = kinds.get(s.error or "?", 0) + 1
        for kind, n in sorted(kinds.items(), key=lambda kv: -kv[1]):
            print(f"      {n:>5}  {kind}")
    if handshakes:
        print(
            f"  handshake (s):    p50={_pct(handshakes, 50):.3f}  "
            f"p95={_pct(handshakes, 95):.3f}  max={max(handshakes):.3f}"
        )
    print(f"  streams w/o ping: {len(no_ping)} (of {len(connected)} held)")
    if fanout:
        print(
            f"  fan-out (s):      p50={_pct(fanout, 50):.3f}  "
            f"p95={_pct(fanout, 95):.3f}  max={max(fanout):.3f}  "
            f"delivered={len(fanout)}/{len(connected)}"
        )
        print(f"  fan-out mean:     {statistics.mean(fanout):.3f}s")
    else:
        print("  fan-out:          no broadcast measured")
    print(f"  wall time:        {wall:.1f}s")
    print("=" * 60)

    ok = len(connected) == run.connections and not errored
    if fanout:
        ok = ok and len(fanout) == len(connected)
    return ok


async def main() -> int:
    parser = argparse.ArgumentParser(description="SSE connection-soak + fan-out test")
    parser.add_argument("-n", "--connections", type=int, default=250)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--nats-url", default="nats://127.0.0.1:4222")
    parser.add_argument(
        "--hold",
        type=float,
        default=20.0,
        help="Seconds to hold all streams open before the broadcast (>=16 to "
        "observe at least one 15s heartbeat ping).",
    )
    parser.add_argument(
        "--no-broadcast",
        action="store_true",
        help="Soak only: skip the NATS fan-out measurement.",
    )
    parser.add_argument(
        "--ramp",
        type=float,
        default=0.0,
        help="Seconds to spread connection opens over (0 = all at once).",
    )
    args = parser.parse_args()

    run = Run(
        connections=args.connections,
        base_url=args.base_url,
        nats_url=args.nats_url,
        hold_seconds=args.hold,
    )
    run.stats = [ConnStats() for _ in range(args.connections)]

    wall_start = time.perf_counter()
    readies = [asyncio.Event() for _ in range(args.connections)]
    tasks: list[asyncio.Task] = []
    per_open_delay = (args.ramp / args.connections) if args.ramp else 0.0
    for i in range(args.connections):
        tasks.append(asyncio.create_task(_run_stream(run, i, readies[i])))
        if per_open_delay:
            await asyncio.sleep(per_open_delay)

    # Wait until every stream has either handshaked or failed, so the soak
    # window and the broadcast run against a fully-open fleet.
    await asyncio.gather(*(r.wait() for r in readies))
    established = sum(1 for s in run.stats if s.connected)
    print(f"[t+{time.perf_counter() - wall_start:.1f}s] {established} streams open")

    await asyncio.sleep(args.hold)

    if not args.no_broadcast:
        print(f"[t+{time.perf_counter() - wall_start:.1f}s] publishing broadcast")
        await _publish_broadcast(run)
        # Give slow consumers a moment to receive, then tear down.
        await asyncio.sleep(5.0)

    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)

    ok = _report(run, time.perf_counter() - wall_start)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
