from datetime import datetime
from pathlib import Path
from typing import NewType
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader

JinjaEnvironment = NewType("JinjaEnvironment", Environment)


def _event_time(value: datetime | None, tz: ZoneInfo) -> str:
    """Format a tz-aware instant as local ``HH:MM`` for notification copy.

    Templates receive UTC-aware datetimes; render them in the festival timezone
    so the printed clock time matches what attendees read off the venue clocks.
    Returns an empty string for None so callers can guard with ``{% if %}``.
    """
    if value is None:
        return ""
    return value.astimezone(tz).strftime("%H:%M")


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
    return JinjaEnvironment(environment)
