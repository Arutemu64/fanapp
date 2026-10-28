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
      user id, used as `chat_id`). It is an **address**, never an identity. Both
      providers always supply it — a login or link lacking it is refused
      upstream — and the column is `NOT NULL` to match.

    Keying on `subject` rather than the native id is what OpenID Connect asks a
    relying party to do, and here it is also the more durable choice: Telegram
    lists `sub` in its discovery document's `claims_supported` and `id` not at
    all, and `id` arrives only with the `profile` scope — which Telegram drops
    outright when the bot is switched to EdDSA or ES256K signing in BotFather.

    `messages_allowed` is the last answer the provider gave to "may we message
    this account?", or None before anyone asked. Only VK records it: a VK
    community can write only to users who allowed it, and the API cannot list
    them, so VK asks apps to keep that state themselves (docs/backend.md).
    """

    id: SocialIdentityId
    user_id: UserId
    provider: SocialProvider
    subject: str
    provider_user_id: int
    messages_allowed: bool | None = None

    def record_messages_allowed(self, *, allowed: bool) -> bool:
        """Store the provider's answer; return whether it changed."""
        if self.messages_allowed is allowed:
            return False
        self.messages_allowed = allowed
        return True
