import logging
import typing

import polars as pl

from fanfan.application.interactors.schedule_mgmt.import_schedule import ScheduleEntry
from fanfan.core.exceptions.schedule import (
    InvalidScheduleFile,
    InvalidScheduleFileReason,
)

logger = logging.getLogger(__name__)

# The header names the organizer must put in row 1. Matched by name, so column
# order in the sheet is free. Kept in sync with the template spreadsheet
# (frontend/static/schedule-template.xlsx) by a parser test.
REQUIRED_COLUMNS = (
    "number",
    "title",
    "duration_seconds",
    "nomination_title",
    "block_title",
)

# Row 1 holds the headers, so the first data row is row 2. Reported row numbers
# have to match what the organizer sees in Excel, not the dataframe index.
FIRST_DATA_ROW = 2


def _read_int(value: object, *, column: str, row: int) -> int:
    """Read a whole number from a cell, rejecting anything that is not one.

    Excel has no integer type — a cell holding 1 comes back as 1.0 — so floats
    are accepted when they carry no fractional part and rejected otherwise.
    """
    if value is None:
        raise InvalidScheduleFile(
            InvalidScheduleFileReason.EMPTY_CELL, column=column, row=row
        )
    if isinstance(value, bool):
        raise InvalidScheduleFile(
            InvalidScheduleFileReason.INVALID_NUMBER, column=column, row=row
        )
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)

    raise InvalidScheduleFile(
        InvalidScheduleFileReason.INVALID_NUMBER, column=column, row=row
    )


def _read_text(value: object, *, column: str, row: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidScheduleFile(
            InvalidScheduleFileReason.EMPTY_CELL, column=column, row=row
        )

    return value.strip()


def _read_dataframe(file: typing.BinaryIO) -> pl.DataFrame:
    # fastexcel (the calamine engine) only accepts a path or raw bytes, not a
    # file object, so read the upload into memory before handing it to polars.
    # Cells are left at their native types and coerced per row below, which is
    # what lets a bad value be reported with its column and row — a polars-level
    # cast would fail somewhere inside read_excel with neither.
    try:
        return pl.read_excel(file.read())
    except Exception as e:
        logger.info("Rejected an unreadable schedule file", exc_info=e)
        raise InvalidScheduleFile(InvalidScheduleFileReason.UNREADABLE_FILE) from e


def parse_schedule_from_excel(file: typing.BinaryIO) -> list[ScheduleEntry]:
    schedule_df = _read_dataframe(file)

    missing_columns = [
        column for column in REQUIRED_COLUMNS if column not in schedule_df.columns
    ]
    if missing_columns:
        raise InvalidScheduleFile(
            InvalidScheduleFileReason.MISSING_COLUMNS, columns=missing_columns
        )

    schedule: list[ScheduleEntry] = []
    seen_numbers: set[int] = set()
    for row_index, row in enumerate(
        schedule_df.iter_rows(named=True), start=FIRST_DATA_ROW
    ):
        number = _read_int(row["number"], column="number", row=row_index)
        # The import matches existing events by number and deletes the rest, so a
        # repeated number would update one event and orphan another instead of
        # doing what the organizer meant.
        if number in seen_numbers:
            raise InvalidScheduleFile(
                InvalidScheduleFileReason.DUPLICATE_NUMBER,
                row=row_index,
                number=number,
            )
        seen_numbers.add(number)

        schedule.append(
            ScheduleEntry(
                number=number,
                title=_read_text(row["title"], column="title", row=row_index),
                duration_seconds=_read_int(
                    row["duration_seconds"], column="duration_seconds", row=row_index
                ),
                nomination_title=_read_text(
                    row["nomination_title"], column="nomination_title", row=row_index
                ),
                block_title=_read_text(
                    row["block_title"], column="block_title", row=row_index
                ),
            )
        )

    if not schedule:
        raise InvalidScheduleFile(InvalidScheduleFileReason.EMPTY_FILE)

    return schedule
