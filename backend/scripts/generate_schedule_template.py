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
    "duration_seconds": 18,
    "nomination_title": 26,
    "block_title": 20,
}

# Plausible FAN FAN rows, so the expected shape of every column is obvious at a
# glance — especially `duration_seconds`, which is whole seconds and not a time.
# The single defile is deliberately 30 seconds: short acts are common, and they
# are exactly what the old minutes column could not express.
SAMPLE_ROWS = [
    (1, "Открытие фестиваля", 900, "Вне конкурса", "Открытие"),
    (2, "Дефиле «Наруто»", 30, "Одиночное дефиле", "Косплей"),
    (3, "Сценка «Стальной алхимик»", 300, "Групповое дефиле", "Косплей"),
    (4, "Вокал: «Унесённые призраками»", 240, "Вокал", "Караоке"),
    (5, "Награждение и закрытие", 1200, "Вне конкурса", "Закрытие"),
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
        number, title, duration_seconds, nomination_title, block_title = row
        worksheet.write_number(row_index, 0, number, number_format)
        worksheet.write_string(row_index, 1, title)
        worksheet.write_number(row_index, 2, duration_seconds, number_format)
        worksheet.write_string(row_index, 3, nomination_title)
        worksheet.write_string(row_index, 4, block_title)

    worksheet.freeze_panes(1, 0)
    workbook.close()

    print(f"Wrote {TEMPLATE_PATH}")


if __name__ == "__main__":
    main()
