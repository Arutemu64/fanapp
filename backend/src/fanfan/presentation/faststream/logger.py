import logging


def get_stream_logger() -> logging.Logger:
    """Return the logger FastStream should use for its own messages.

    FastStream uses whatever logger we hand it both for its framework/access
    logs and for the ``Logger`` dependency injected into subscribers. We give it
    a plain stdlib logger with no handlers of its own and ``propagate=True`` so
    every record flows to the root handler configured by ``setup_logging()``
    (structlog). This keeps the stream service consistent with every other
    service: console output in dev, JSON in prod, and the same log level.

    Without a custom logger FastStream falls back to its default, which installs
    its own colorized ``StreamHandler`` with ``propagate=False`` and a fixed
    ``INFO`` level — bypassing structlog entirely, so the service would emit
    colorized plaintext even when ``json_logs`` is enabled in production.

    FastStream forwards its per-message context (message id, channel) through the
    record's ``extra``; ``structlog.stdlib.ExtraAdder`` in the root handler's
    pre-chain surfaces it, so that context is not lost.
    """
    logger = logging.getLogger("faststream")
    # Drop the colorized stderr handler FastStream attaches at import time so
    # records are formatted exactly once, by the root structlog handler.
    logger.handlers.clear()
    logger.propagate = True
    return logger
