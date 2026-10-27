import pytest
from pydantic import HttpUrl, SecretStr

from fanfan.core.vo.social_identity import SocialProvider
from fanfan.presentation.web.config import WebConfig

pytestmark = pytest.mark.unit


def _config(
    enabled_oauth_providers: list[SocialProvider] | None = None,
) -> WebConfig:
    """Builds a config, optionally overriding the OAuth provider list.

    Two explicit constructions rather than one call with a `**overrides` splat:
    a splatted dict cannot be type-checked, and passing the field through
    unconditionally would leave the default-value test asserting its own input.
    """
    if enabled_oauth_providers is None:
        return WebConfig(
            host="localhost",
            port=8000,
            public_url=HttpUrl("http://localhost:3000/"),
            secret_key=SecretStr("test-secret-key"),
        )
    return WebConfig(
        host="localhost",
        port=8000,
        public_url=HttpUrl("http://localhost:3000/"),
        secret_key=SecretStr("test-secret-key"),
        enabled_oauth_providers=enabled_oauth_providers,
    )


def test_oauth_providers_default_to_vk_only() -> None:
    assert _config().enabled_oauth_providers == [SocialProvider.VK]


def test_oauth_providers_preserve_configured_order() -> None:
    config = _config(
        enabled_oauth_providers=[SocialProvider.TELEGRAM, SocialProvider.VK]
    )

    assert config.enabled_oauth_providers == [
        SocialProvider.TELEGRAM,
        SocialProvider.VK,
    ]


def test_oauth_providers_can_be_emptied() -> None:
    assert _config(enabled_oauth_providers=[]).enabled_oauth_providers == []


def test_oauth_providers_are_deduplicated_preserving_order() -> None:
    config = _config(
        enabled_oauth_providers=[
            SocialProvider.TELEGRAM,
            SocialProvider.VK,
            SocialProvider.TELEGRAM,
        ]
    )

    assert config.enabled_oauth_providers == [
        SocialProvider.TELEGRAM,
        SocialProvider.VK,
    ]
