from contextlib import suppress

import uvicorn

from fanfan.adapters.config.parsers import get_config
from fanfan.presentation.web.factory import create_app


def main():
    config = get_config()
    create_app()
    with suppress(KeyboardInterrupt):
        uvicorn.run(
            "fanfan.presentation.web.factory:create_app",
            factory=True,
            reload=True,
            host=config.web.host,
            port=config.web.port,
            root_path="/api",
            forwarded_allow_ips=["*"],
            log_level=config.debug.logging_level,
            log_config=None,
        )


if __name__ == "__main__":
    main()
