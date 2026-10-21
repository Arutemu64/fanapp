from fanfan.core.events.base import Message


class Command(Message):
    """An instruction to do work later: imperative, exactly one handler.

    Enqueued with ``UnitOfWork.enqueue`` when it must survive alongside the
    transaction that asked for it, or published with ``EventBroker`` from a
    consumer that is already redelivered on failure (ADR-0040).
    """
