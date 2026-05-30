import typing

import sentry_sdk
from faststream import BaseMiddleware

if typing.TYPE_CHECKING:
    from types import TracebackType


class SentryMiddleware(BaseMiddleware):
    async def after_processed(
        self,
        exc_type: type[BaseException] | None = None,
        exc_val: BaseException | None = None,
        exc_tb: TracebackType | None = None,
    ) -> bool | None:
        if exc_val is not None:
            sentry_sdk.capture_exception(exc_val)
        return await super().after_processed(exc_type, exc_val, exc_tb)
