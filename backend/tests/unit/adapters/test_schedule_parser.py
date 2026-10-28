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
    duration_seconds=900,
    nomination_title="Вне конкурса",
)
VALID_ROW: dict[str, object] = dict(VALID_ENTRY.model_dump())
VALID_ROW["type"] = None


def valid_row(**overrides: object) -> tuple[object, ...]:
    """A row that parses cleanly, in REQUIRED_COLUMNS order, with cells swapped."""
    cells = VALID_ROW | overrides
    return tuple(cells[column] for column in REQUIRED_COLUMNS)


def block_row(title: str, **overrides: object) -> tuple[object, ...]:
    """A block row: type and title only, unless overridden."""
    cells = dict.fromkeys(REQUIRED_COLUMNS) | {"type": "block", "title": title}
    cells |= overrides
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
            duration_seconds=900,
            nomination_title=None,
        ),
        ScheduleBlockRow(title="Косплей"),
        ScheduleEventRow(
            number=1,
            title="Дефиле «Наруто»",
            duration_seconds=45,
            nomination_title="Одиночное дефиле",
        ),
        ScheduleEventRow(
            number=2,
            title="Сценка «Стальной алхимик»",
            duration_seconds=480,
            nomination_title="Групповое дефиле",
        ),
        ScheduleEventRow(
            number=None,
            title="Перерыв",
            duration_seconds=600,
            nomination_title=None,
        ),
        ScheduleBlockRow(title="Караоке"),
        ScheduleEventRow(
            number=3,
            title="Вокал: «Унесённые призраками»",
            duration_seconds=210,
            nomination_title="Вокал",
        ),
        ScheduleBlockRow(title="Закрытие"),
        ScheduleEventRow(
            number=None,
            title="Награждение и закрытие",
            duration_seconds=1200,
            nomination_title=None,
        ),
    ]


def test_column_order_does_not_matter() -> None:
    sheet = build_sheet(
        ["type", "duration_seconds", "number", "nomination_title", "title"],
        [(None, 900, 1, "Вне конкурса", "Открытие фестиваля")],
    )

    assert parse_schedule_from_excel(sheet) == [VALID_ENTRY]


def test_accepts_whole_numbers_stored_as_floats() -> None:
    sheet = build_sheet(
        REQUIRED_COLUMNS, [valid_row(number=1.0, duration_seconds=900.0)]
    )

    assert parse_schedule_from_excel(sheet) == [VALID_ENTRY]


def test_accepts_a_sub_minute_duration() -> None:
    sheet = build_sheet(REQUIRED_COLUMNS, [valid_row(duration_seconds=45)])

    assert parse_schedule_from_excel(sheet) == [
        VALID_ENTRY.model_copy(update={"duration_seconds": 45})
    ]


def test_rejects_a_file_that_is_not_a_spreadsheet() -> None:
    with pytest.raises(InvalidScheduleFile) as exc_info:
        parse_schedule_from_excel(io.BytesIO(b"definitely not a spreadsheet"))

    assert exc_info.value.details["reason"] == InvalidScheduleFileReason.UNREADABLE_FILE


def test_reports_every_missing_column_at_once() -> None:
    sheet = build_sheet(["number", "title", "type"], [(1, "Открытие", None)])

    with pytest.raises(InvalidScheduleFile) as exc_info:
        parse_schedule_from_excel(sheet)

    assert exc_info.value.details["reason"] == InvalidScheduleFileReason.MISSING_COLUMNS
    assert exc_info.value.details["columns"] == ["duration_seconds", "nomination_title"]


def test_rejects_an_empty_sheet() -> None:
    sheet = build_sheet(REQUIRED_COLUMNS, [])

    with pytest.raises(InvalidScheduleFile) as exc_info:
        parse_schedule_from_excel(sheet)

    assert exc_info.value.details["reason"] == InvalidScheduleFileReason.EMPTY_FILE


def test_rejects_a_blank_title() -> None:
    sheet = build_sheet(
        REQUIRED_COLUMNS,
        [valid_row(), valid_row(number=2, title="   ")],
    )

    with pytest.raises(InvalidScheduleFile) as exc_info:
        parse_schedule_from_excel(sheet)

    assert exc_info.value.details["reason"] == InvalidScheduleFileReason.EMPTY_CELL
    assert exc_info.value.details["column"] == "title"
    assert exc_info.value.details["row"] == 3


@pytest.mark.parametrize("blank", [None, "", "   "])
def test_accepts_a_blank_nomination(blank: object) -> None:
    sheet = build_sheet(REQUIRED_COLUMNS, [valid_row(nomination_title=blank)])

    schedule = parse_schedule_from_excel(sheet)

    assert schedule == [VALID_ENTRY.model_copy(update={"nomination_title": None})]


@pytest.mark.parametrize("row_type", [None, "", "   ", "event", "Event"])
def test_a_blank_or_event_type_is_an_event_row(row_type: object) -> None:
    sheet = build_sheet(REQUIRED_COLUMNS, [valid_row(type=row_type)])

    assert parse_schedule_from_excel(sheet) == [VALID_ENTRY]


def test_a_block_row_starts_a_block() -> None:
    sheet = build_sheet(
        REQUIRED_COLUMNS,
        [block_row("  Косплей ", type=" Block "), valid_row()],
    )

    assert parse_schedule_from_excel(sheet) == [
        ScheduleBlockRow(title="Косплей"),
        VALID_ENTRY,
    ]


def test_rejects_an_unknown_type() -> None:
    sheet = build_sheet(REQUIRED_COLUMNS, [valid_row(type="блок")])

    with pytest.raises(InvalidScheduleFile) as exc_info:
        parse_schedule_from_excel(sheet)

    assert exc_info.value.details["reason"] == InvalidScheduleFileReason.INVALID_TYPE
    assert exc_info.value.details["column"] == "type"
    assert exc_info.value.details["row"] == 2


def test_rejects_a_block_row_without_a_title() -> None:
    sheet = build_sheet(REQUIRED_COLUMNS, [block_row("  ")])

    with pytest.raises(InvalidScheduleFile) as exc_info:
        parse_schedule_from_excel(sheet)

    assert exc_info.value.details["reason"] == InvalidScheduleFileReason.EMPTY_CELL
    assert exc_info.value.details["column"] == "title"


@pytest.mark.parametrize(
    ("column", "value"),
    [("number", 1), ("duration_seconds", 60), ("nomination_title", "Х")],
)
def test_rejects_a_block_row_with_event_cells(column: str, value: object) -> None:
    sheet = build_sheet(REQUIRED_COLUMNS, [block_row("Косплей", **{column: value})])

    with pytest.raises(InvalidScheduleFile) as exc_info:
        parse_schedule_from_excel(sheet)

    assert (
        exc_info.value.details["reason"]
        == InvalidScheduleFileReason.BLOCK_ROW_WITH_EVENT_DATA
    )
    assert exc_info.value.details["column"] == column
    assert exc_info.value.details["row"] == 2


@pytest.mark.parametrize("column", ["number", "duration_seconds"])
def test_rejects_a_non_integer_number(column: str) -> None:
    sheet = build_sheet(REQUIRED_COLUMNS, [valid_row(**{column: "пять"})])

    with pytest.raises(InvalidScheduleFile) as exc_info:
        parse_schedule_from_excel(sheet)

    assert exc_info.value.details["reason"] == InvalidScheduleFileReason.INVALID_NUMBER
    assert exc_info.value.details["column"] == column
    assert exc_info.value.details["row"] == 2


def test_rejects_a_fractional_duration() -> None:
    sheet = build_sheet(REQUIRED_COLUMNS, [valid_row(duration_seconds=7.5)])

    with pytest.raises(InvalidScheduleFile) as exc_info:
        parse_schedule_from_excel(sheet)

    assert exc_info.value.details["reason"] == InvalidScheduleFileReason.INVALID_NUMBER
    assert exc_info.value.details["column"] == "duration_seconds"


@pytest.mark.parametrize("duration_seconds", [0, -60])
def test_rejects_a_duration_that_is_not_positive(duration_seconds: int) -> None:
    sheet = build_sheet(
        REQUIRED_COLUMNS, [valid_row(duration_seconds=duration_seconds)]
    )

    with pytest.raises(InvalidScheduleFile) as exc_info:
        parse_schedule_from_excel(sheet)

    assert (
        exc_info.value.details["reason"]
        == InvalidScheduleFileReason.DURATION_NOT_POSITIVE
    )
    assert exc_info.value.details["column"] == "duration_seconds"


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
