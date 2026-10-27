import time
import typing

import sentry_sdk
from faststream import BaseMiddleware
from nats.aio.msg import Msg
from sentry_sdk.tracing import Span, TransactionSource

from fanfan.adapters.debug.tracing import current_trace_headers

if typing.TYPE_CHECKING:
    from types import TracebackType

    from faststream.message import StreamMessage
    from faststream.response import PublishCommand

_PUBLISH_OP = "queue.publish"
_PROCESS_OP = "queue.process"


class SentryMiddleware(BaseMiddleware):
    """Report consumer errors and carry Sentry traces across NATS.

    A publish made inside a traced request or handler stamps the trace headers
    on the message; the consumer continues that trace, so one request's work is
    one trace across the web app, the outbox relay and every consumer.
    """

    _reported: BaseException | None = None

    async def publish_scope(
        self,
        call_next: typing.Callable[[PublishCommand], typing.Awaitable[typing.Any]],
        cmd: PublishCommand,
    ) -> typing.Any:  # noqa: ANN401
        if sentry_sdk.get_current_span() is None:
            return await call_next(cmd)
        with sentry_sdk.start_span(op=_PUBLISH_OP, name=cmd.destination) as span:
            span.set_data("messaging.destination.name", cmd.destination)
            for name, value in current_trace_headers().items():
                cmd.headers.setdefault(name, value)
            return await call_next(cmd)

    async def consume_scope(
        self,
        call_next: typing.Callable[
            [StreamMessage[typing.Any]], typing.Awaitable[typing.Any]
        ],
        msg: StreamMessage[typing.Any],
    ) -> typing.Any:  # noqa: ANN401
        with sentry_sdk.isolation_scope():
            name = _consumer_name(msg)
            transaction = sentry_sdk.continue_trace(
                dict(msg.headers),
                op=_PROCESS_OP,
                name=name,
                source=TransactionSource.TASK,
            )
            with (
                sentry_sdk.start_transaction(transaction),
                sentry_sdk.start_span(op=_PROCESS_OP, name=name) as span,
            ):
                _describe_message(span, msg)
                try:
                    return await call_next(msg)
                except Exception as error:
                    sentry_sdk.capture_exception(error)
                    self._reported = error
                    raise

    async def after_processed(
        self,
        exc_type: type[BaseException] | None = None,
        exc_val: BaseException | None = None,
        exc_tb: TracebackType | None = None,
    ) -> bool | None:
        if exc_val is not None and exc_val is not self._reported:
            sentry_sdk.capture_exception(exc_val)
        return await super().after_processed(exc_type, exc_val, exc_tb)


def _consumer_name(msg: StreamMessage[typing.Any]) -> str:
    raw = msg.raw_message
    if isinstance(raw, Msg) and raw.reply.startswith("$JS.ACK."):
        return raw.metadata.consumer or raw.subject
    if isinstance(raw, Msg):
        return raw.subject
    return "nats.message"


def _describe_message(span: Span, msg: StreamMessage[typing.Any]) -> None:
    raw = msg.raw_message
    if not isinstance(raw, Msg):
        return
    span.set_data("messaging.message.id", msg.message_id)
    span.set_data("messaging.destination.name", raw.subject)
    span.set_data("messaging.message.body.size", len(raw.data))
    if not raw.reply.startswith("$JS.ACK."):
        return
    metadata = raw.metadata
    span.set_data("messaging.message.retry.count", metadata.num_delivered - 1)
    stored_at = metadata.timestamp.timestamp()
    span.set_data("messaging.message.receive.latency", (time.time() - stored_at) * 1000)
