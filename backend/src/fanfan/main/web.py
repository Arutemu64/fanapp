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
            reload=config.debug.enabled,
            host=config.web.host,
            port=config.web.port,
            root_path="/api",
            forwarded_allow_ips=["*"],
            timeout_graceful_shutdown=5,
            log_level=config.debug.logging_level,
            log_config=None,
            loop="asyncio:SelectorEventLoop" if sys.platform == "win32" else "auto",
        )


if __name__ == "__main__":
    main()
