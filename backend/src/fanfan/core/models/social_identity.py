from dataclasses import dataclass

from fanfan.core.models.base import AggregateRoot
from fanfan.core.vo.social_identity import SocialIdentityId, SocialProvider
from fanfan.core.vo.user import UserId


@dataclass(slots=True, kw_only=True)
class SocialIdentity(AggregateRoot):
    """A link between a local user and one external account.

    The two provider-side values are deliberately separate, because they are
    different numbers with different jobs — Telegram's own sample token pairs
    `id: 987654321` with `sub: "1234123412341234123"`:

    * `subject` is the provider's stable account identifier (for Telegram, the
      OIDC `sub`). It is the **identity key** — the only value matched on at
      login — and is never used to call the provider's API.
    * `provider_user_id` is the provider's native account id (Telegram's Bot API
      user id, used as `chat_id`). It is an **address**, never an identity, and
      is optional: a token issued for `openid` alone carries no such id, and a
      provider used only for signing in never needs one.

    Keying on `subject` rather than the native id is what OpenID Connect asks a
    relying party to do, and here it is also the more durable choice: Telegram
    lists `sub` in its discovery document's `claims_supported` and `id` not at
    all, and `id` arrives only with the `profile` scope — which Telegram drops
    outright when the bot is switched to EdDSA or ES256K signing in BotFather.
    """

    id: SocialIdentityId
    user_id: UserId
    provider: SocialProvider
    subject: str
    provider_user_id: int | None
