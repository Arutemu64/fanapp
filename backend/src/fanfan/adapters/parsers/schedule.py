import logging
import typing

import polars as pl

from fanfan.application.interactors.schedule_mgmt.import_schedule import ScheduleEntry

logger = logging.getLogger(__name__)

# Coerce each column to a known type on read. Numbers stored as floats in Excel
# (e.g. 1.0) are cast to int, and empty cells become None instead of NaN.
_SCHEMA_OVERRIDES = {
    "number": pl.Int64,
    "title": pl.String,
    "duration": pl.Int64,
    "nomination_title": pl.String,
    "block_title": pl.String,
}


def parse_schedule_from_excel(file: typing.BinaryIO) -> list[ScheduleEntry]:
    # fastexcel (the calamine engine) only accepts a path or raw bytes, not a
    # file object, so read the upload into memory before handing it to polars.
    schedule_df = pl.read_excel(file.read(), schema_overrides=_SCHEMA_OVERRIDES)
    return [
        ScheduleEntry(
            number=row["number"],
            title=row["title"],
            duration=row["duration"],
            block_title=row["block_title"],
            nomination_title=row["nomination_title"],
        )
        for row in schedule_df.iter_rows(named=True)
    ]
