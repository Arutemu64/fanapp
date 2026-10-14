import io
from collections.abc import Sequence

import pytest
import xlsxwriter

from fanfan.adapters.parsers.schedule import REQUIRED_COLUMNS, parse_schedule_from_excel
from fanfan.application.interactors.schedule_mgmt.import_schedule import (
    ScheduleBlockRow,
    ScheduleEventRow,
)
from fanfan.common.paths import REPO_ROOT
from fanfan.core.exceptions.schedule import (
    InvalidScheduleFile,
    InvalidScheduleFileReason,
)

pytestmark = pytest.mark.unit

TEMPLATE_PATH = REPO_ROOT / "frontend" / "static" / "schedule-template.xlsx"

VALID_ENTRY = ScheduleEventRow(
    number=1,
    title="Открытие фестиваля",
    duration=900,
    nomination_title="Вне конкурса",
)
# The same entry as spreadsheet cells, keyed by column name. Derived from the
# entry rather than written twice, so the row and the expected parse result
# cannot drift apart. An event row leaves block_title blank.
VALID_ROW: dict[str, object] = VALID_ENTRY.model_dump() | {"block_title": None}


def valid_row(**overrides: object) -> tuple[object, ...]:
    """A row that parses cleanly, in REQUIRED_COLUMNS order, with cells swapped."""
    cells = VALID_ROW | overrides
    return tuple(cells[column] for column in REQUIRED_COLUMNS)


def block_row(block_title: str, **overrides: object) -> tuple[object, ...]:
    """A block heading row: only block_title, unless overridden."""
    cells = dict.fromkeys(REQUIRED_COLUMNS) | {"block_title": block_title} | overrides
    return tuple(cells[column] for column in REQUIRED_COLUMNS)


def build_sheet(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> io.BytesIO:
    buffer = io.BytesIO()
    workbook = xlsxwriter.Workbook(buffer, {"in_memory": True})
    worksheet = workbook.add_worksheet()
    for column_index, header in enumerate(headers):
        worksheet.write_string(0, column_index, header)
    for row_index, row in enumerate(rows, start=1):
        for column_index, value in enumerate(row):
            worksheet.write(row_index, column_index, value)
    workbook.close()
    buffer.seek(0)
    return buffer


def test_parses_the_downloadable_template() -> None:
    """The template offered on the import screen must parse as-is.

    This is the drift guard for a committed binary: change the columns the
    parser requires without regenerating the template
    (`just backend-generate-schedule-template`) and this fails.
    """
    with TEMPLATE_PATH.open("rb") as file:
        schedule = parse_schedule_from_excel(file)

    assert schedule == [
        ScheduleEventRow(
            number=None,
            title="Открытие фестиваля",
            duration=900,
            nomination_title=None,
        ),
        ScheduleBlockRow(title="Косплей"),
        ScheduleEventRow(
            number=1,
            title="Дефиле «Наруто»",
            duration=45,
            nomination_title="Одиночное дефиле",
        ),
        ScheduleEventRow(
            number=2,
            title="Сценка «Стальной алхимик»",
            duration=480,
            nomination_title="Групповое дефиле",
        ),
        ScheduleEventRow(
            number=None,
            title="Перерыв",
            duration=600,
            nomination_title=None,
        ),
        ScheduleBlockRow(title="Караоке"),
        ScheduleEventRow(
            number=3,
            title="Вокал: «Унесённые призраками»",
            duration=210,
            nomination_title="Вокал",
        ),
        ScheduleBlockRow(title="Закрытие"),
        ScheduleEventRow(
            number=None,
            title="Награждение и закрытие",
            duration=1200,
            nomination_title=None,
        ),
    ]


def test_column_order_does_not_matter() -> None:
    sheet = build_sheet(
        ["block_title", "duration", "number", "nomination_title", "title"],
        [(None, 900, 1, "Вне конкурса", "Открытие фестиваля")],
    )

    assert parse_schedule_from_excel(sheet) == [VALID_ENTRY]


def test_accepts_whole_numbers_stored_as_floats() -> None:
    # Excel has no integer type, so a hand-typed 1 can arrive as 1.0.
    sheet = build_sheet(REQUIRED_COLUMNS, [valid_row(number=1.0, duration=900.0)])

    assert parse_schedule_from_excel(sheet) == [VALID_ENTRY]


def test_accepts_a_sub_minute_duration() -> None:
    # `duration` is seconds, so an act shorter than a minute is an ordinary
    # value rather than something to round up — a single defile really does run
    # under a minute.
    sheet = build_sheet(REQUIRED_COLUMNS, [valid_row(duration=45)])

    assert parse_schedule_from_excel(sheet) == [
        VALID_ENTRY.model_copy(update={"duration": 45})
    ]


def test_rejects_a_file_that_is_not_a_spreadsheet() -> None:
    with pytest.raises(InvalidScheduleFile) as exc_info:
        parse_schedule_from_excel(io.BytesIO(b"definitely not a spreadsheet"))

    assert exc_info.value.details["reason"] == InvalidScheduleFileReason.UNREADABLE_FILE


def test_reports_every_missing_column_at_once() -> None:
    sheet = build_sheet(["number", "title", "block_title"], [(1, "Открытие", "Блок")])

    with pytest.raises(InvalidScheduleFile) as exc_info:
        parse_schedule_from_excel(sheet)

    assert exc_info.value.details["reason"] == InvalidScheduleFileReason.MISSING_COLUMNS
    assert exc_info.value.details["columns"] == ["duration", "nomination_title"]


def test_rejects_an_empty_sheet() -> None:
    sheet = build_sheet(REQUIRED_COLUMNS, [])

    with pytest.raises(InvalidScheduleFile) as exc_info:
        parse_schedule_from_excel(sheet)

    assert exc_info.value.details["reason"] == InvalidScheduleFileReason.EMPTY_FILE


def test_rejects_a_blank_title() -> None:
    # `title` is an event row's only human identity, so it stays required even
    # though the nomination is optional.
    sheet = build_sheet(
        REQUIRED_COLUMNS,
        [valid_row(), valid_row(number=2, title="   ")],
    )

    with pytest.raises(InvalidScheduleFile) as exc_info:
        parse_schedule_from_excel(sheet)

    assert exc_info.value.details["reason"] == InvalidScheduleFileReason.EMPTY_CELL
    assert exc_info.value.details["column"] == "title"
    # Row 1 is the header and row 2 is the valid entry, so the bad one is row 3.
    assert exc_info.value.details["row"] == 3


@pytest.mark.parametrize("blank", [None, "", "   "])
def test_accepts_a_blank_nomination(blank: object) -> None:
    # Breaks, the opening and the closing carry no nomination, so the cell may
    # be blank — an empty cell, an empty string or whitespace all read back as
    # None rather than forcing an invented placeholder.
    sheet = build_sheet(REQUIRED_COLUMNS, [valid_row(nomination_title=blank)])

    schedule = parse_schedule_from_excel(sheet)

    assert schedule == [VALID_ENTRY.model_copy(update={"nomination_title": None})]


@pytest.mark.parametrize("blank", ["", "   "])
def test_a_blank_block_title_is_an_event_row(blank: object) -> None:
    sheet = build_sheet(REQUIRED_COLUMNS, [valid_row(block_title=blank)])

    assert parse_schedule_from_excel(sheet) == [VALID_ENTRY]


def test_a_block_title_row_starts_a_block() -> None:
    sheet = build_sheet(
        REQUIRED_COLUMNS,
        [block_row("  Косплей "), valid_row()],
    )

    assert parse_schedule_from_excel(sheet) == [
        ScheduleBlockRow(title="Косплей"),
        VALID_ENTRY,
    ]


@pytest.mark.parametrize(
    ("column", "value"),
    [("number", 1), ("title", "Дефиле"), ("duration", 60), ("nomination_title", "Х")],
)
def test_rejects_a_block_row_with_event_cells(column: str, value: object) -> None:
    # The old layout repeated block_title beside every event; reading such a
    # file as blocks would turn every act into a heading.
    sheet = build_sheet(REQUIRED_COLUMNS, [block_row("Косплей", **{column: value})])

    with pytest.raises(InvalidScheduleFile) as exc_info:
        parse_schedule_from_excel(sheet)

    assert (
        exc_info.value.details["reason"]
        == InvalidScheduleFileReason.BLOCK_ROW_WITH_EVENT_DATA
    )
    assert exc_info.value.details["column"] == column
    assert exc_info.value.details["row"] == 2


@pytest.mark.parametrize("column", ["number", "duration"])
def test_rejects_a_non_integer_number(column: str) -> None:
    sheet = build_sheet(REQUIRED_COLUMNS, [valid_row(**{column: "пять"})])

    with pytest.raises(InvalidScheduleFile) as exc_info:
        parse_schedule_from_excel(sheet)

    assert exc_info.value.details["reason"] == InvalidScheduleFileReason.INVALID_NUMBER
    assert exc_info.value.details["column"] == column
    assert exc_info.value.details["row"] == 2


def test_rejects_a_fractional_duration() -> None:
    sheet = build_sheet(REQUIRED_COLUMNS, [valid_row(duration=7.5)])

    with pytest.raises(InvalidScheduleFile) as exc_info:
        parse_schedule_from_excel(sheet)

    assert exc_info.value.details["reason"] == InvalidScheduleFileReason.INVALID_NUMBER
    assert exc_info.value.details["column"] == "duration"


def test_rejects_a_repeated_number() -> None:
    sheet = build_sheet(REQUIRED_COLUMNS, [valid_row(), valid_row(title="Другое")])

    with pytest.raises(InvalidScheduleFile) as exc_info:
        parse_schedule_from_excel(sheet)

    assert (
        exc_info.value.details["reason"] == InvalidScheduleFileReason.DUPLICATE_NUMBER
    )
    assert exc_info.value.details["number"] == 1
    assert exc_info.value.details["row"] == 3


def test_accepts_an_empty_number() -> None:
    # Breaks carry no public number, so `number` is the one column that may be
    # left blank.
    sheet = build_sheet(
        REQUIRED_COLUMNS,
        [valid_row(), valid_row(number=None, title="Перерыв")],
    )

    schedule = parse_schedule_from_excel(sheet)

    assert schedule == [
        VALID_ENTRY,
        VALID_ENTRY.model_copy(update={"number": None, "title": "Перерыв"}),
    ]


def test_accepts_several_numberless_rows() -> None:
    # Numberless rows match no existing event, so they never collide the way two
    # rows sharing a number would.
    sheet = build_sheet(
        REQUIRED_COLUMNS,
        [
            valid_row(number=None, title="Перерыв"),
            valid_row(number=None, title="Технический перерыв"),
        ],
    )

    schedule = parse_schedule_from_excel(sheet)

    assert schedule == [
        VALID_ENTRY.model_copy(update={"number": None, "title": "Перерыв"}),
        VALID_ENTRY.model_copy(update={"number": None, "title": "Технический перерыв"}),
    ]


def test_skips_a_blank_row_and_keeps_excel_row_numbers() -> None:
    # A gap left between acts is not an act with an empty title, and a bad cell
    # after the gap is reported at the row the organizer sees in Excel.
    sheet = build_sheet(
        REQUIRED_COLUMNS,
        [valid_row(), (None,) * len(REQUIRED_COLUMNS), valid_row(number=2, title="")],
    )

    with pytest.raises(InvalidScheduleFile) as exc_info:
        parse_schedule_from_excel(sheet)

    assert exc_info.value.details["column"] == "title"
    assert exc_info.value.details["row"] == 4


def test_rejects_a_workbook_with_no_cells() -> None:
    sheet = build_sheet([], [])

    with pytest.raises(InvalidScheduleFile) as exc_info:
        parse_schedule_from_excel(sheet)

    assert exc_info.value.details["reason"] == InvalidScheduleFileReason.EMPTY_FILE
