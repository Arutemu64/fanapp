from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from dishka import AsyncContainer
from procrastinate import Blueprint, JobContext
from procrastinate.tasks import Task

from fanfan.adapters.procrastinate.job_queue import MessageRoutes
from fanfan.core.events.base import Message
from fanfan.presentation.worker.retry import BoundedBackoff

# Key of the worker's APP container in JobContext.additional_context, set by
# main/worker.py when it starts the worker.
CONTAINER_CONTEXT_KEY = "container"


@dataclass(frozen=True, slots=True)
class Delivery:
    """What a subscriber gets besides its message."""

    # A REQUEST scope opened for this job, like an HTTP request gets.
    container: AsyncContainer
    # When the transaction that queued the message committed.
    occurred_at: datetime


type Subscriber[M: Message] = Callable[[M, Delivery], Awaitable[None]]

_routes: defaultdict[str, list[Task[Any, Any, Any]]] = defaultdict(list)


def subscriber[M: Message](
    blueprint: Blueprint, message_type: type[M], *, name: str
) -> Callable[[Subscriber[M]], Subscriber[M]]:
    """Register a task that runs once for every ``message_type`` queued.

    Each subscriber of a subject gets its own job, so one subscriber failing and
    retrying never reruns the others. ``name`` is stored on every job row, so
    renaming it strands queued jobs: treat it as a contract, like ``subject``.
    """

    def decorator(handler: Subscriber[M]) -> Subscriber[M]:
        async def run(
            context: JobContext,
            *,
            message: dict[str, Any],
            occurred_at: str,
            # Read from the job by the Sentry middleware, not here.
            trace_headers: dict[str, str] | None = None,
        ) -> None:
            app_container: AsyncContainer = context.additional_context[
                CONTAINER_CONTEXT_KEY
            ]
            async with app_container() as container:
                delivery = Delivery(
                    container=container,
                    occurred_at=datetime.fromisoformat(occurred_at),
                )
                await handler(message_type.model_validate(message), delivery)

        task = blueprint.task(name=name, pass_context=True, retry=BoundedBackoff())(run)
        _routes[message_type.subject].append(task)
        return handler

    return decorator


def message_routes() -> MessageRoutes:
    """Every subscribed subject and its tasks, for the job queue adapter."""
    return _routes
