from fanfan.adapters.serialization import create_retort
from fanfan.core.models.app_settings import AppSettings, ScheduleConfig


def test_settings_saved_before_a_section_existed_load_with_its_defaults() -> None:
    """The settings row is one JSONB document with no migration per section, so a
    row stored before a section was added must still load, the section taking its
    defaults."""
    retort = create_retort()
    stored = retort.dump(AppSettings())
    del stored["schedule"]

    loaded = retort.load(stored, AppSettings)

    assert loaded.schedule == ScheduleConfig()
