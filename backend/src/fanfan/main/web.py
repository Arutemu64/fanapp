from contextlib import suppress

import uvicorn

from fanfan.adapters.config.parsers import get_config


def main():
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
            log_level=config.debug.logging_level,
            log_config=None,
        )


if __name__ == "__main__":
    main()
