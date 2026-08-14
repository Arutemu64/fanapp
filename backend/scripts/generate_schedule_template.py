#!/usr/bin/env python3
#
# Regenerate the schedule-import template spreadsheet offered for download on
# /tools/import_schedule. Driven by `just backend-generate-schedule-template`.
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
    "number": 10,
    "title": 38,
    "duration": 11,
    "nomination_title": 26,
    "block_title": 20,
}

# Plausible FAN FAN rows, so the expected shape of every column is obvious at a
# glance — especially `duration`, which is whole *seconds* rather than minutes or
# a time. The single-defile row is deliberately under a minute: an act that short
# is real (walk on, pose, walk off), and it is the case a minutes column could
# not express at all.
#
# The opening, the break and the closing leave `number`, `nomination_title` and
# `block_title` all blank on purpose: those cells may be empty, and an organizer
# is far likelier to copy the shape from the template than to read it in the
# guide. The break sits *between* the Косплей and Караоке blocks, modelling the
# recommended shape — a block-less row renders as an interlude between sections,
# so keeping mid-block pauses out of this sample avoids teaching a split block.
# `None` for a text cell is written as a blank cell below.
SAMPLE_ROWS = [
    (None, "Открытие фестиваля", 900, None, None),
    (1, "Дефиле «Наруто»", 45, "Одиночное дефиле", "Косплей"),
    (2, "Сценка «Стальной алхимик»", 480, "Групповое дефиле", "Косплей"),
    (None, "Перерыв", 600, None, None),
    (3, "Вокал: «Унесённые призраками»", 210, "Вокал", "Караоке"),
    (None, "Награждение и закрытие", 1200, None, None),
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
        number, title, duration, nomination_title, block_title = row
        if number is not None:
            worksheet.write_number(row_index, 0, number, number_format)
        worksheet.write_string(row_index, 1, title)
        worksheet.write_number(row_index, 2, duration, number_format)
        # Left blank for interludes (breaks, opening, closing) — a blank cell is
        # what the parser reads back as "no nomination / no block".
        if nomination_title is not None:
            worksheet.write_string(row_index, 3, nomination_title)
        if block_title is not None:
            worksheet.write_string(row_index, 4, block_title)

    worksheet.freeze_panes(1, 0)
    workbook.close()

    print(f"Wrote {TEMPLATE_PATH}")


if __name__ == "__main__":
    main()
