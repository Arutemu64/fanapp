import asyncio
import sys
from collections.abc import Callable, Mapping

import pytest

pytest_plugins = ["tests.fixtures.tracing", "tests.fixtures.users"]

_TIER_BY_DIR = {"unit": "unit", "integration": "integration"}


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Mark every test by the tier directory it lives in.

    `--strict-markers` rejects unknown markers but not missing ones, so an
    unmarked test would silently drop out of both `-m unit` and `-m integration`.
    The directory is the single source of truth; a test outside both tiers, or
    one carrying the other tier's marker, is a collection error.
    """
    tests_root = config.rootpath / "tests"
    for item in items:
        tier = _TIER_BY_DIR.get(item.path.relative_to(tests_root).parts[0])
        if tier is None:
            msg = f"{item.nodeid}: must live under tests/unit/ or tests/integration/"
            raise pytest.UsageError(msg)
        other = "integration" if tier == "unit" else "unit"
        if item.get_closest_marker(other) is not None:
            msg = f"{item.nodeid}: marked '{other}' but lives under tests/{tier}/"
            raise pytest.UsageError(msg)
        item.add_marker(tier)


if sys.platform == "win32":
    # psycopg's async mode cannot run on Windows' default ProactorEventLoop;
    # same constraint as fanfan/adapters/db/event_loop.py.
    def pytest_asyncio_loop_factories(
        config: pytest.Config,
        item: pytest.Item,
    ) -> Mapping[str, Callable[[], asyncio.AbstractEventLoop]]:
        return {"selector": asyncio.SelectorEventLoop}
