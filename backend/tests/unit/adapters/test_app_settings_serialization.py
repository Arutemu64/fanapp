from fanfan.adapters.db.gateways.app_settings import _from_model, _to_model
from fanfan.adapters.db.models import AppSettingsORM
from fanfan.core.events.base import DomainEvent
from fanfan.core.models.app_settings import AppSettings, ScheduleConfig


def test_settings_saved_before_a_section_existed_load_with_its_defaults() -> None:
    row = AppSettingsORM(id=1, config={"quest": {"enabled": True}})

    loaded = _to_model(row)

    assert loaded.quest.enabled
    assert loaded.schedule == ScheduleConfig()


def test_pending_events_stay_out_of_settings_json() -> None:
    settings = AppSettings()
    settings.record_event(DomainEvent())

    row = _from_model(settings)

    assert "_events" not in row.config
    assert _to_model(row) == settings
    assert len(settings.pull_events()) == 1
