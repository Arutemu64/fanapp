#!/usr/bin/env python3
#
# Regenerate the schedule-import template spreadsheet offered for download on
# /tools/schedule. Driven by `just backend-generate-schedule-template`.
#
# The template is committed as a binary, so this script is what makes it
# reviewable: the headers and the sample rows live here in plain text. Keep the
# headers equal to REQUIRED_COLUMNS in the parser — a parser test feeds the
# committed file back through parse_schedule_from_excel and fails on drift.
import xlsxwriter

from fanfan.adapters.parsers.schedule import REQUIRED_COLUMNS
from fanfan.common.paths import REPO_ROOT

TEMPLATE_PATH = REPO_ROOT / "frontend" / "static" / "schedule-template.xlsx"

# Widths are eyeballed per column so the sample text is readable without the
# organizer having to resize anything before they start editing.
COLUMN_WIDTHS = {
    "type": 9,
    "number": 10,
    "title": 38,
    "duration": 11,
    "nomination_title": 26,
}

# Plausible FAN FAN rows, so the expected shape of every column is obvious at a
# glance — especially `duration`, which is whole *seconds* rather than minutes or
# a time. The single-defile row is deliberately under a minute: an act that short
# is real (walk on, pose, walk off), and it is the case a minutes column could
# not express at all.
#
# Block rows are typed `block` and carry only a title: each starts a block that
# runs until the next one, so the sample shows the shape an organizer copies far
# more readily than reading it in the guide. Event rows leave `type` blank, the
# common case. The opening sits above the first block and so belongs to none;
# the break sits at the end of the Косплей block, where a pause between two
# blocks necessarily lands.
#
# The opening, the break and the closing leave `number` and `nomination_title`
# blank on purpose: those cells may be empty. `None` for a cell is written as a
# blank cell below.
SAMPLE_ROWS = [
    (None, None, "Открытие фестиваля", 900, None),
    ("block", None, "Косплей", None, None),
    (None, 1, "Дефиле «Наруто»", 45, "Одиночное дефиле"),
    (None, 2, "Сценка «Стальной алхимик»", 480, "Групповое дефиле"),
    (None, None, "Перерыв", 600, None),
    ("block", None, "Караоке", None, None),
    (None, 3, "Вокал: «Унесённые призраками»", 210, "Вокал"),
    ("block", None, "Закрытие", None, None),
    (None, None, "Награждение и закрытие", 1200, None),
]


def main() -> None:
    workbook = xlsxwriter.Workbook(str(TEMPLATE_PATH))
    worksheet = workbook.add_worksheet("Программа")

    header_format = workbook.add_format(
        {"bold": True, "bg_color": "#F3F4F6", "border": 1}
    )
    number_format = workbook.add_format({"num_format": "0"})

    for column_index, column in enumerate(REQUIRED_COLUMNS):
        worksheet.write_string(0, column_index, column, header_format)
        worksheet.set_column(column_index, column_index, COLUMN_WIDTHS[column])

    for row_index, row in enumerate(SAMPLE_ROWS, start=1):
        # `None` is left as a blank cell: what the parser reads back as "no
        # value" (an event row's type, a break's number or nomination).
        for column_index, value in enumerate(row):
            if isinstance(value, str):
                worksheet.write_string(row_index, column_index, value)
            elif isinstance(value, int):
                worksheet.write_number(row_index, column_index, value, number_format)

    worksheet.freeze_panes(1, 0)
    workbook.close()

    print(f"Wrote {TEMPLATE_PATH}")


if __name__ == "__main__":
    main()
