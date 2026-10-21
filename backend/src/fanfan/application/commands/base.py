from fanfan.core.events.base import Message


class Command(Message):
    """An instruction to do work later: imperative, exactly one handler.

    Enqueued with ``UnitOfWork.enqueue``, so it is queued in the same
    transaction as the change that asked for it (ADR-0040, ADR-0041).
    """
