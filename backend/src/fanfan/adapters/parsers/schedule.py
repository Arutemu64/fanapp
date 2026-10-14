import logging
import typing

from python_calamine import CalamineWorkbook

from fanfan.application.interactors.schedule_mgmt.import_schedule import (
    ScheduleBlockRow,
    ScheduleEventRow,
    ScheduleRow,
)
from fanfan.core.exceptions.schedule import (
    InvalidScheduleFile,
    InvalidScheduleFileReason,
)

logger = logging.getLogger(__name__)

# The header names the organizer must put in row 1. Matched by name, so column
# order in the sheet is free. Kept in sync with the template spreadsheet
# (frontend/static/schedule-template.xlsx) by a parser test.
#
# `duration` is read as whole **seconds** and stored unconverted, because that is
# the unit every consumer downstream already uses (ADR-0008 projects expected
# start times with `timedelta(seconds=duration)`). Minutes here would both
# misreport every projection by 60x and make a sub-minute act unrepresentable.
#
# `type` says what a row is: blank or `event` for an event, `block` for the start
# of a block, whose `title` is the block's name. The event rows below a block
# row, up to the next one, belong to that block. Blank means event because
# nearly every row is one.
REQUIRED_COLUMNS = ("type", "number", "title", "duration", "nomination_title")
EVENT_ROW_TYPE = "event"
BLOCK_ROW_TYPE = "block"
# Cells only an event row may fill; a block row carries just its title.
EVENT_ONLY_COLUMNS = ("number", "duration", "nomination_title")


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


def _read_optional_int(value: object, *, column: str, row: int) -> int | None:
    """Read a whole number from a cell that is allowed to be empty.

    Empty means an actually blank cell. A cell holding whitespace is text, not a
    blank, so it is rejected like any other text instead of silently read as
    "no number".
    """
    if value is None:
        return None

    return _read_int(value, column=column, row=row)


def _read_text(value: object, *, column: str, row: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidScheduleFile(
            InvalidScheduleFileReason.EMPTY_CELL, column=column, row=row
        )

    return value.strip()


def _is_blank(value: object) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _read_optional_text(value: object, *, column: str, row: int) -> str | None:
    """Read text from a cell that is allowed to be empty.

    Breaks, the opening and the closing carry no nomination, so that cell may be
    left blank instead of forcing the organizer to invent a placeholder. A blank
    cell (None, or a string that is only whitespace) means "no value"; anything
    else is read as ordinary text.
    """
    if _is_blank(value):
        return None

    return _read_text(value, column=column, row=row)


def _read_rows(file: typing.BinaryIO) -> list[tuple[int, list[object]]]:
    """Read the first sheet as ``(Excel row number, cells)`` pairs.

    Cells keep their native types and are coerced per row by the readers above,
    which is what lets a bad value be reported with its column and row.

    calamine reports an empty cell as ``""``; it becomes ``None`` here so the
    readers have a single notion of "blank". Wholly blank rows are skipped, so a
    gap left between acts is not reported as a row with an empty title.
    """
    try:
        sheet = CalamineWorkbook.from_filelike(file).get_sheet_by_index(0)
        # Keep the leading empty area so a list index maps straight onto the
        # row number the organizer sees in Excel.
        cells = sheet.to_python(skip_empty_area=False)
    except Exception as e:
        logger.info("Rejected an unreadable schedule file", exc_info=e)
        raise InvalidScheduleFile(InvalidScheduleFileReason.UNREADABLE_FILE) from e

    rows: list[tuple[int, list[object]]] = []
    for row_number, row in enumerate(cells, start=1):
        values: list[object] = [None if cell == "" else cell for cell in row]
        if any(value is not None for value in values):
            rows.append((row_number, values))
    return rows


def _index_columns(header: list[object]) -> dict[str, int]:
    """Map each header name to its column index; the first of a repeat wins."""
    columns: dict[str, int] = {}
    for index, name in enumerate(header):
        if isinstance(name, str) and name not in columns:
            columns[name] = index
    return columns


def _read_row_type(value: object, *, row: int) -> str:
    row_type = _read_optional_text(value, column="type", row=row)
    if row_type is None:
        return EVENT_ROW_TYPE
    # Matched case-insensitively: "Block" typed by hand means the same thing.
    row_type = row_type.lower()
    if row_type not in {EVENT_ROW_TYPE, BLOCK_ROW_TYPE}:
        raise InvalidScheduleFile(
            InvalidScheduleFileReason.INVALID_TYPE, column="type", row=row
        )
    return row_type


def _read_block_row(row: dict[str, object], row_index: int) -> ScheduleBlockRow:
    for column in EVENT_ONLY_COLUMNS:
        if not _is_blank(row[column]):
            raise InvalidScheduleFile(
                InvalidScheduleFileReason.BLOCK_ROW_WITH_EVENT_DATA,
                column=column,
                row=row_index,
            )
    return ScheduleBlockRow(
        title=_read_text(row["title"], column="title", row=row_index)
    )


def parse_schedule_from_excel(file: typing.BinaryIO) -> list[ScheduleRow]:
    rows = _read_rows(file)
    if not rows:
        raise InvalidScheduleFile(InvalidScheduleFileReason.EMPTY_FILE)

    # The first non-blank row holds the headers.
    _, header = rows[0]
    data_rows = rows[1:]
    columns = _index_columns(header)

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in columns]
    if missing_columns:
        raise InvalidScheduleFile(
            InvalidScheduleFileReason.MISSING_COLUMNS, columns=missing_columns
        )

    schedule: list[ScheduleRow] = []
    seen_numbers: set[int] = set()
    for row_index, values in data_rows:
        row = {column: values[index] for column, index in columns.items()}

        if _read_row_type(row["type"], row=row_index) == BLOCK_ROW_TYPE:
            schedule.append(_read_block_row(row, row_index))
            continue

        # An empty number is allowed — breaks and other filler rows have none.
        number = _read_optional_int(row["number"], column="number", row=row_index)
        # The import matches existing events by number and deletes the rest, so a
        # repeated number would update one event and orphan another instead of
        # doing what the organizer meant. Numberless rows match nothing, so any
        # number of them may coexist.
        if number is not None:
            if number in seen_numbers:
                raise InvalidScheduleFile(
                    InvalidScheduleFileReason.DUPLICATE_NUMBER,
                    row=row_index,
                    number=number,
                )
            seen_numbers.add(number)

        schedule.append(
            ScheduleEventRow(
                number=number,
                title=_read_text(row["title"], column="title", row=row_index),
                duration=_read_int(row["duration"], column="duration", row=row_index),
                nomination_title=_read_optional_text(
                    row["nomination_title"], column="nomination_title", row=row_index
                ),
            )
        )

    if not schedule:
        raise InvalidScheduleFile(InvalidScheduleFileReason.EMPTY_FILE)

    return schedule
