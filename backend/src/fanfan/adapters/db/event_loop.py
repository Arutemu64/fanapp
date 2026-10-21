import asyncio
import sys
from collections.abc import Callable


def loop_factory() -> Callable[[], asyncio.AbstractEventLoop]:
    """The `loop_factory` for every `asyncio.run` that may touch the database.

    psycopg's async mode cannot run on Windows' default ProactorEventLoop
    (https://www.psycopg.org/psycopg3/docs/advanced/async.html), so local
    Windows runs get the selector loop. Everywhere else gets uvloop, the same
    loop uvicorn picks for the web process (ADR-0039); it is not installed on
    Windows, hence the import inside the branch.
    """
    if sys.platform == "win32":
        return asyncio.SelectorEventLoop

    import uvloop  # noqa: PLC0415 — absent on Windows, see above

    return uvloop.new_event_loop
