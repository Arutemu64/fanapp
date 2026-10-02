import asyncio
import sys
from collections.abc import Callable


def loop_factory() -> Callable[[], asyncio.AbstractEventLoop] | None:
    """The `loop_factory` for every `asyncio.run` that may touch the database.

    psycopg's async mode cannot run on Windows' default ProactorEventLoop
    (https://www.psycopg.org/psycopg3/docs/advanced/async.html), so local
    Windows runs get the selector loop. None keeps asyncio's default elsewhere.
    """
    if sys.platform == "win32":
        return asyncio.SelectorEventLoop
    return None
