#!/usr/bin/env python3
import xlsxwriter

from fanfan.adapters.parsers.schedule import REQUIRED_COLUMNS
from fanfan.common.paths import REPO_ROOT

TEMPLATE_PATH = REPO_ROOT / "frontend" / "static" / "schedule-template.xlsx"

COLUMN_WIDTHS = {
    "type": 9,
    "number": 10,
    "title": 38,
    "duration_seconds": 11,
    "nomination_title": 26,
}

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
