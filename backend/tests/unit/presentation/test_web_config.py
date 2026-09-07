import pytest
from pydantic import HttpUrl, SecretStr

from fanfan.core.vo.social_identity import SocialProvider
from fanfan.presentation.web.config import WebConfig

pytestmark = pytest.mark.unit


def _config(**overrides: object) -> WebConfig:
    return WebConfig(
        host="localhost",
        port=8000,
        public_url=HttpUrl("http://localhost:3000/"),
        secret_key=SecretStr("test-secret-key"),
        **overrides,
    )


# The default is a product contract, not a formality: the deployed app relies on
# it to keep VK login working on the next release without setting the new var, and
# to leave Telegram off (its OAuth is unreachable from the production host).
def test_oauth_providers_default_to_vk_only():
    assert _config().enabled_oauth_providers == [SocialProvider.VK]


def test_oauth_providers_preserve_configured_order():
    config = _config(
        enabled_oauth_providers=[SocialProvider.TELEGRAM, SocialProvider.VK]
    )

    # The login screen renders buttons in this order, so it must round-trip as set.
    assert config.enabled_oauth_providers == [
        SocialProvider.TELEGRAM,
        SocialProvider.VK,
    ]


def test_oauth_providers_can_be_emptied():
    assert _config(enabled_oauth_providers=[]).enabled_oauth_providers == []


# A repeated id (a config typo) would collide the keyed `{#each provider}` on the
# frontend, so the config normalises to a unique list, keeping first-seen order.
def test_oauth_providers_are_deduplicated_preserving_order():
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
