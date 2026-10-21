from types import SimpleNamespace
from typing import Any, cast

import pytest
from nats.js.api import StreamConfig

from fanfan.presentation.faststream.jstream import retire_stream_subjects, stream

pytestmark = pytest.mark.unit


class _FakeJetStream:
    def __init__(self, subjects: list[str]) -> None:
        self.config = StreamConfig(name=stream.name, subjects=subjects, max_age=60)
        self.updates: list[StreamConfig] = []

    async def stream_info(self, _name: str) -> SimpleNamespace:
        return SimpleNamespace(config=self.config)

    async def update_stream(self, config: StreamConfig) -> None:
        self.updates.append(config)


def _broker(js: _FakeJetStream) -> Any:  # noqa: ANN401  # stands in for NatsBroker
    connection = SimpleNamespace(jetstream=lambda: js)
    return cast("Any", SimpleNamespace(connection=connection))


@pytest.mark.asyncio
async def test_retired_subjects_are_removed_and_the_rest_kept() -> None:
    js = _FakeJetStream(["cmd.sync.run", "sse.broadcast.*", "sse.user.*.*"])

    await retire_stream_subjects(_broker(js))

    [update] = js.updates
    assert update.subjects == ["cmd.sync.run"]
    # The rest of the server's config is sent back unchanged.
    assert update.max_age == js.config.max_age


@pytest.mark.asyncio
async def test_stream_without_retired_subjects_is_not_updated() -> None:
    js = _FakeJetStream(["cmd.sync.run"])

    await retire_stream_subjects(_broker(js))

    assert js.updates == []


def test_stream_does_not_capture_sse_subjects() -> None:
    # Live updates go over core NATS and nothing replays them.
    assert not any(subject.startswith("sse.") for subject in stream.subjects)
