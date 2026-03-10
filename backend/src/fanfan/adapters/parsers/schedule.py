import logging
import typing

import numpy as np
import pandas as pd

from fanfan.application.schedule_mgmt.import_schedule import ScheduleEntry
from fanfan.core.vo.schedule_event import ScheduleEventPublicNumber

logger = logging.getLogger(__name__)

ORDER_INIT = 100.0
ORDER_STEP = 100.0


def parse_schedule_from_excel(file: typing.BinaryIO) -> list[ScheduleEntry]:
    schedule_df = pd.read_excel(
        file,
        converters={
            "public_number": int,
            "title": str,
            "duration": int,
            "nomination_title": str,
            "block_title": str,
        },
    )
    schedule_df = schedule_df.replace({np.nan: None})
    return [
        ScheduleEntry(
            public_number=ScheduleEventPublicNumber(row["public_number"]),
            title=row["title"],
            duration=row["duration"],
            block_title=row["block_title"],
            nomination_title=row["nomination_title"],
        )
        for _index, row in schedule_df.iterrows()
    ]
