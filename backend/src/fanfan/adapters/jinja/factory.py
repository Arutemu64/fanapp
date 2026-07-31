from datetime import datetime
from pathlib import Path
from typing import NewType
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader

JinjaEnvironment = NewType("JinjaEnvironment", Environment)

SECONDS_PER_MINUTE = 60
MINUTES_PER_HOUR = 60


def _event_time(value: datetime | None, tz: ZoneInfo) -> str:
    """Format a tz-aware instant as local ``HH:MM`` for notification copy.

    Templates receive UTC-aware datetimes; render them in the festival timezone
    so the printed clock time matches what attendees read off the venue clocks.
    Returns an empty string for None so callers can guard with ``{% if %}``.

    No template uses this since subscription pushes moved to a relative wait
    (ADR-0013); it stays because rendering a festival-local clock time is a
    general need and the timezone plumbing exists for it.
    """
    if value is None:
        return ""
    return value.astimezone(tz).strftime("%H:%M")


def _approximate_wait(seconds: int | None) -> str:
    """Format a wait in seconds as approximate Russian copy, e.g. ``1 ч 30 мин``.

    Mirrors ``formatApproximateWait`` in the frontend's ``lib/utils/formatters.ts``
    so a push and the schedule screen word the same wait the same way. Rounds to
    the nearest minute: the value is a projection, and printing it to the second
    would claim a precision the schedule does not have.

    Floored at one minute rather than reading "меньше минуты", which does not fit
    the "примерно через …" the push wraps this in. The queue count beside it is
    what tells a reader the act is imminent.
    """
    if seconds is None:
        return ""

    total_minutes = max(1, round(seconds / SECONDS_PER_MINUTE))
    if total_minutes < MINUTES_PER_HOUR:
        return f"{total_minutes} мин"

    hours, minutes = divmod(total_minutes, MINUTES_PER_HOUR)
    if minutes == 0:
        return f"{hours} ч"
    return f"{hours} ч {minutes} мин"


def create_jinja_env(timezone: str) -> JinjaEnvironment:
    templates_path = Path(__file__).parent.joinpath("templates")
    environment = Environment(
        lstrip_blocks=True,
        trim_blocks=True,
        loader=FileSystemLoader(searchpath=templates_path),
        enable_async=True,
        autoescape=True,
    )
    tz = ZoneInfo(timezone)
    environment.filters["event_time"] = lambda value: _event_time(value, tz)
    environment.filters["approximate_wait"] = _approximate_wait
    return JinjaEnvironment(environment)
