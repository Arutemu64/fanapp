from adaptix import Retort

from fanfan.adapters.db.models import AppSettingsORM
from fanfan.core.models.app_settings import AppSettings


class AppSettingsMapper:
    def __init__(self, retort: Retort):
        self.retort = retort

    def from_model(self, model: AppSettings) -> AppSettingsORM:
        return AppSettingsORM(id=1, config=self.retort.dump(model))

    def to_model(self, orm: AppSettingsORM) -> AppSettings:
        return self.retort.load(orm.config, AppSettings)
