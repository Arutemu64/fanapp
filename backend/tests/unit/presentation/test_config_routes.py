from http import HTTPStatus

import pytest
from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from starlette.testclient import TestClient

from fanfan.application.interactors.settings.get_public_config import GetPublicConfig
from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.core.models.app_settings import AppSettings
from fanfan.presentation.web.routes.config import config_router
from fanfan.presentation.web.routes.settings import settings_router

pytestmark = pytest.mark.unit


class _FakeAppSettingsGateway(AppSettingsGateway):
    async def get(self) -> AppSettings:
        return AppSettings()

    async def get_for_update(self) -> AppSettings:
        return AppSettings()

    async def save(self, settings: AppSettings) -> None:
        pass


class _ConfigProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def get_public_config(self) -> GetPublicConfig:
        return GetPublicConfig(_FakeAppSettingsGateway())


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(config_router)
    app.include_router(settings_router)
    setup_dishka(make_async_container(_ConfigProvider()), app)
    return TestClient(app, raise_server_exceptions=False)


def test_config_is_served_for_revalidation(client: TestClient) -> None:
    response = client.get("/config")

    assert response.status_code == HTTPStatus.OK
    assert response.headers["Cache-Control"] == "no-cache"
    assert response.headers["ETag"].startswith('"')
    assert "festival_start" in response.json()


def test_config_answers_a_held_version_with_304(client: TestClient) -> None:
    etag = client.get("/config").headers["ETag"]

    response = client.get("/config", headers={"If-None-Match": etag})

    assert response.status_code == HTTPStatus.NOT_MODIFIED
    assert response.headers["ETag"] == etag
    assert response.content == b""


def test_settings_patch_without_if_match_is_rejected(client: TestClient) -> None:
    # Rejected before the interactor (which this container does not provide)
    # is ever resolved: an unconditional save must be asked for with `*`.
    response = client.patch("/settings", json={})

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert "if-match" in response.text
