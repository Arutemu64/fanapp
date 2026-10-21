import asyncio

from dishka_faststream import setup_dishka
from faststream.asgi import AsgiFastStream, make_ping_asgi

from fanfan.adapters.config.parsers import get_config
from fanfan.adapters.db.event_loop import loop_factory
from fanfan.adapters.debug.logging import HEALTH_CHECK_PATH
from fanfan.main.common import init
from fanfan.main.di import create_system_container
from fanfan.presentation.faststream.broker import create_broker
from fanfan.presentation.faststream.jstream import retire_stream_subjects
from fanfan.presentation.faststream.logger import get_stream_logger
from fanfan.presentation.faststream.redelivery import sync_consumer_configs
from fanfan.presentation.faststream.routes import setup_router

# How long the health route waits for the broker to report a live connection.
# Below the 3 s urlopen timeout of the image's HEALTHCHECK (backend/Dockerfile),
# so a disconnected broker answers 500 instead of timing the probe out.
_HEALTH_PING_TIMEOUT_SECONDS = 2.0


def create_app() -> AsgiFastStream:
    init(service_name="stream")

    config = get_config()
    broker = create_broker(config=config.nats, name="fanfan-consumer")
    broker.include_router(setup_router())

    # ASGI only to serve the image's HEALTHCHECK on the path the api uses, so
    # `docker ps` shows a consumer that has lost NATS as unhealthy.
    # https://faststream.ag2.ai/0.7/getting-started/observability/healthcheks/
    app = AsgiFastStream(
        broker,
        asgi_routes=[
            (
                HEALTH_CHECK_PATH,
                make_ping_asgi(
                    broker,
                    timeout=_HEALTH_PING_TIMEOUT_SECONDS,
                    include_in_schema=False,
                ),
            ),
        ],
        logger=get_stream_logger(),
    )

    @app.after_startup
    async def _apply_server_config() -> None:
        await retire_stream_subjects(broker)
        await sync_consumer_configs(broker)

    container = create_system_container()
    setup_dishka(container, app)

    return app


def main() -> None:
    app = create_app()
    # Off 8000, the api's port on the host; mirrors `just backend-stream`.
    asyncio.run(app.run(run_extra_options={"port": 8001}), loop_factory=loop_factory())


if __name__ == "__main__":
    main()
