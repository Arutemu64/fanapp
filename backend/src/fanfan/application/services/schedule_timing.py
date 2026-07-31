from datetime import datetime

from fanfan.application.dto.schedule import ScheduleEventFullDTO
from fanfan.core.vo.schedule_event import ScheduleEventId


def project_seconds_until(
    events: list[ScheduleEventFullDTO],
    *,
    transition_buffer_seconds: int,
    now: datetime,
) -> dict[ScheduleEventId, int]:
    """How long until each upcoming event starts, in seconds, keyed by event id.

    See ADR-0013. The act on stage anchors the walk: whatever is left of its
    planned ``duration_seconds`` (floored at zero, because an overrunning act has
    no planned time left) plus a ``transition_buffer_seconds`` changeover, then
    each following act's duration and changeover in turn.

    ``events`` must be ordered by ``order`` (as ``read_list_schedule`` returns
    them). The current event, everything before it, and skipped events are absent
    from the result: the first two have no wait to report and the third consumes
    no stage time. An empty dict means nothing is on stage yet, so there is no
    anchor to measure from.

    The frontend mirrors this in ``lib/utils/scheduleTiming.ts`` to keep the wait
    live between fetches; this copy renders the same wait into subscription push
    text, where there is no client to do the work.
    """
    current = next((e for e in events if e.is_current), None)
    if current is None or current.actual_start_time is None:
        return {}

    elapsed_seconds = (now - current.actual_start_time).total_seconds()
    # An act that has run past its planned length owes no more stage time, but
    # the changeover below still has to happen — which is what stops the wait
    # from going negative once a show starts slipping.
    remaining_current_seconds = max(0.0, current.duration_seconds - elapsed_seconds)

    seconds_until: dict[ScheduleEventId, int] = {}
    running_seconds = remaining_current_seconds
    anchor_passed = False
    for event in events:
        if not anchor_passed:
            if event is current:
                anchor_passed = True
            continue
        if event.is_skipped:
            continue
        running_seconds += transition_buffer_seconds
        seconds_until[event.id] = int(running_seconds)
        running_seconds += event.duration_seconds

    return seconds_until
