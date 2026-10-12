import sys
from contextlib import suppress

import uvicorn

from fanfan.adapters.config.parsers import get_config


def main() -> None:
    config = get_config()
    with suppress(KeyboardInterrupt):
        uvicorn.run(
            "fanfan.presentation.web.factory:create_app",
            factory=True,
            # Auto-reload is a development convenience only; never run it
            # against a production deployment.
            reload=config.debug.enabled,
            host=config.web.host,
            port=config.web.port,
            root_path="/api",
            forwarded_allow_ips=["*"],
            # Bounds the wait on open SSE streams, which never end on their
            # own; see UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN in docker-compose.yml.
            timeout_graceful_shutdown=5,
            log_level=config.debug.logging_level,
            log_config=None,
            # psycopg's async mode cannot run on Windows' default
            # ProactorEventLoop; same constraint as adapters/db/event_loop.py.
            loop="asyncio:SelectorEventLoop" if sys.platform == "win32" else "auto",
        )


if __name__ == "__main__":
    main()
