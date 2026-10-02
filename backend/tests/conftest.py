import asyncio
import sys
from collections.abc import Callable, Mapping

import pytest

pytest_plugins = ["tests.fixtures.tracing", "tests.fixtures.users"]

if sys.platform == "win32":
    # psycopg's async mode cannot run on Windows' default ProactorEventLoop;
    # same constraint as fanfan/adapters/db/event_loop.py.
    def pytest_asyncio_loop_factories(
        config: pytest.Config,
        item: pytest.Item,
    ) -> Mapping[str, Callable[[], asyncio.AbstractEventLoop]]:
        return {"selector": asyncio.SelectorEventLoop}
