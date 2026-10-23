from types import SimpleNamespace
from typing import Any, cast

import pytest
from nats.js.errors import BadRequestError, NotFoundError

from fanfan.presentation.faststream.jstream import scheduler_stream
from fanfan.presentation.faststream.schedules.config import SchedulerConfig
from fanfan.presentation.faststream.schedules.jobs import (
    OUTBOX_RETENTION,
    SCHEDULED_JOBS,
    SYNC_TCLOUD,
    schedule_headers,
    scheduled_crons,
    sync_schedules,
)

pytestmark = pytest.mark.unit

_TZ = "Europe/Moscow"


class _FakeJetStream:
    def __init__(self, stored: dict[str, dict[str, str]] | None = None) -> None:
        # Schedule subject -> headers of the message the server holds there.
        self.stored = stored or {}
        self.published: dict[str, dict[str, str]] = {}
        self.purged: list[str] = []
        self.rejected: set[str] = set()

    async def get_last_msg(self, stream: str, subject: str) -> SimpleNamespace:
        assert stream == scheduler_stream.name
        if subject not in self.stored:
            raise NotFoundError
        return SimpleNamespace(headers=self.stored[subject])

    async def publish(
        self, subject: str, *, stream: str, headers: dict[str, str]
    ) -> None:
        assert stream == scheduler_stream.name
        if subject in self.rejected:
            raise BadRequestError
        self.published[subject] = headers

    async def purge_stream(self, stream: str, *, subject: str) -> None:
        assert stream == scheduler_stream.name
        self.purged.append(subject)


def _broker(js: _FakeJetStream) -> Any:  # noqa: ANN401  # stands in for NatsBroker
    connection = SimpleNamespace(jetstream=lambda: js)
    return cast("Any", SimpleNamespace(connection=connection))


def test_every_config_field_maps_to_a_job() -> None:
    crons = scheduled_crons(SchedulerConfig())

    assert set(crons) == set(SCHEDULED_JOBS)
    assert len(SchedulerConfig.model_fields) == len(SCHEDULED_JOBS)


def test_crontab_gets_a_seconds_field_and_the_app_time_zone() -> None:
    headers = schedule_headers(SYNC_TCLOUD, "*/15 * * * *", _TZ)

    assert headers == {
        "Nats-Schedule": "0 */15 * * * *",
        "Nats-Schedule-Target": "scheduler.tick.sync_tcloud",
        "Nats-Schedule-Time-Zone": _TZ,
    }


@pytest.mark.parametrize("cron", ["30 0 4 * * *", "@daily"])
def test_nats_cron_passes_through(cron: str) -> None:
    headers = schedule_headers(SYNC_TCLOUD, cron, _TZ)

    assert headers["Nats-Schedule"] == cron
    assert headers["Nats-Schedule-Time-Zone"] == _TZ


def test_interval_has_no_time_zone() -> None:
    # The server rejects a time zone on anything but a cron schedule.
    headers = schedule_headers(SYNC_TCLOUD, "@every 1h", _TZ)

    assert headers["Nats-Schedule"] == "@every 1h"
    assert "Nats-Schedule-Time-Zone" not in headers


@pytest.mark.asyncio
async def test_enabled_job_is_published_and_disabled_ones_purged() -> None:
    js = _FakeJetStream()
    config = SchedulerConfig(sync_tcloud_cron="0 * * * *")

    await sync_schedules(_broker(js), config, _TZ)

    assert list(js.published) == [SYNC_TCLOUD.schedule_subject]
    # The tick too, so one left from when the job was enabled doesn't linger.
    assert OUTBOX_RETENTION.schedule_subject in js.purged
    assert OUTBOX_RETENTION.tick_subject in js.purged
    assert SYNC_TCLOUD.schedule_subject not in js.purged


@pytest.mark.asyncio
async def test_unchanged_schedule_is_not_republished() -> None:
    # Republishing would restart an @every interval on every deploy.
    stored = schedule_headers(SYNC_TCLOUD, "@every 1h", _TZ)
    stored_with_server_headers = {**stored, "Nats-Rollup": "sub"}
    js = _FakeJetStream({SYNC_TCLOUD.schedule_subject: stored_with_server_headers})

    config = SchedulerConfig(sync_tcloud_cron="@every 1h")

    await sync_schedules(_broker(js), config, _TZ)

    assert js.published == {}


@pytest.mark.asyncio
async def test_dropped_header_counts_as_a_change() -> None:
    stored = schedule_headers(SYNC_TCLOUD, "0 * * * *", _TZ)
    js = _FakeJetStream({SYNC_TCLOUD.schedule_subject: stored})

    config = SchedulerConfig(sync_tcloud_cron="@every 1h")

    await sync_schedules(_broker(js), config, _TZ)

    published = js.published[SYNC_TCLOUD.schedule_subject]
    assert "Nats-Schedule-Time-Zone" not in published


@pytest.mark.asyncio
async def test_rejected_schedule_does_not_stop_the_rest() -> None:
    js = _FakeJetStream()
    js.rejected.add(SYNC_TCLOUD.schedule_subject)
    config = SchedulerConfig(
        sync_tcloud_cron="not a cron", outbox_retention_cron="0 4 * * *"
    )

    await sync_schedules(_broker(js), config, _TZ)

    assert list(js.published) == [OUTBOX_RETENTION.schedule_subject]
