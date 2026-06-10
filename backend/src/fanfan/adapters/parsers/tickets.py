import logging
from typing import BinaryIO

import polars as pl
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.models import TicketORM
from fanfan.core.vo.user import UserRole

logger = logging.getLogger(__name__)


async def parse_tickets(file: BinaryIO, session: AsyncSession) -> None:
    # fastexcel (the calamine engine) only accepts a path or raw bytes, not a
    # file object, so read the upload into memory before handing it to polars.
    tickets_df = pl.read_excel(
        file.read(),
        schema_overrides={"id": pl.String, "role": pl.String},
    )
    for row in tickets_df.iter_rows(named=True):
        ticket_id = row["id"]
        role = UserRole(row["role"])
        try:
            async with session.begin_nested():
                session.add(TicketORM(id=ticket_id, role=role))
            logger.info("Parsed ticket %s with role %s", ticket_id, role)
        except IntegrityError:
            ticket = await session.get(TicketORM, ticket_id)
            if not ticket:
                raise
            logger.info("Ticket %s already exist", ticket_id)
    await session.commit()
