from datetime import datetime, timedelta

from fanfan.application.dto.schedule import ScheduleEventFullDTO


def apply_expected_start_times(
    events: list[ScheduleEventFullDTO],
    *,
    transition_buffer: int,
    now: datetime,
) -> list[ScheduleEventFullDTO]:
    """Fill ``expected_start_time`` on each event from the live show anchor.

    See ADR-0008. The current event's real ``actual_start_time`` is the anchor;
    every later non-skipped event is projected forward by its predecessors'
    ``duration`` plus a ``transition_buffer`` gap. Each projection is floored at
    ``now + transition_buffer`` so an overrunning current act pushes the whole
    tail forward instead of predicting times already in the past.

    ``events`` must be ordered by ``order`` (as ``read_list_schedule`` returns
    them). Events before the current one, skipped events, and the case where
    nothing is on stage yet are left with ``expected_start_time = None`` — there
    is no anchor to project from. The list is mutated in place and returned.
    """
    current = next((e for e in events if e.is_current), None)
    if current is None or current.actual_start_time is None:
        return events

    anchor = current.actual_start_time
    current.expected_start_time = anchor

    # Walk the events after the anchor in order, carrying a running clock. The
    # gap added before each event is the *previous* event's duration + buffer,
    # so the running value always names the next event's projected start.
    running = anchor
    previous_duration = current.duration
    anchor_passed = False
    for event in events:
        if not anchor_passed:
            # Fast-forward to just past the current event; earlier events keep
            # their None projection.
            if event is current:
                anchor_passed = True
            continue
        if event.is_skipped:
            # Skipped events consume no stage time and get no projected start.
            continue
        running = running + timedelta(seconds=previous_duration + transition_buffer)
        # Floor at now + buffer so an overrunning current act pushes the tail
        # forward instead of predicting a start already in the past. The floor
        # keeps the buffer because even if the overrunning act ended this
        # instant, the transition would still have to happen. Carrying the
        # clamped value forward cascades the drift to later events (where the
        # floor can no longer bind, since each step already adds the buffer).
        running = max(running, now + timedelta(seconds=transition_buffer))
        event.expected_start_time = running
        previous_duration = event.duration

    return events
