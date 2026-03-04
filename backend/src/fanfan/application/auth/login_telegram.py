# id, first_name, last_name, username, photo_url, auth_date and hash fields
import hashlib
import hmac
import time

from aiogram import Bot
from pydantic import BaseModel

from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.core.dto.token import Token
from fanfan.core.models.social_account import SocialAccount
from fanfan.core.models.user import User
from fanfan.core.services.security import SecurityService
from fanfan.core.services.user import UserService
from fanfan.core.vo.user import UserRole
from fanfan.presentation.tgbot.config import BotConfig


class LoginTelegramCommand(BaseModel):
    id: int
    first_name: str
    auth_date: int
    hash: str
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None


class LoginTelegram:
    def __init__(
        self,
        bot: Bot,
        bot_config: BotConfig,
        user_gateway: UserGateway,
        security: SecurityService,
        uow: UnitOfWork,
        user_service: UserService,
    ) -> None:
        self.uow = uow
        self.security = security
        self.user_gateway = user_gateway
        self.bot = bot
        self.bot_config = bot_config
        self.user_service = user_service

    @staticmethod
    def check_telegram_authorization(auth_data: dict, bot_token: str) -> dict:
        # Create a copy so we don't mutate the original dictionary
        data = auth_data.copy()

        if "hash" not in data:
            msg = "Hash is missing"
            raise ValueError(msg)

        check_hash = data.pop("hash")

        # Format the data as "key=value" and sort it alphabetically
        data_check_arr = [f"{key}={value}" for key, value in data.items()]
        data_check_arr.sort()

        # Join the sorted array with newlines
        data_check_string = "\n".join(data_check_arr)

        # Generate the secret key (SHA256 hash of the bot token, outputting raw bytes)
        secret_key = hashlib.sha256(bot_token.encode("utf-8")).digest()

        # Generate the HMAC-SHA256 signature
        calculated_hash = hmac.new(
            secret_key, data_check_string.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        # Compare the hashes securely to prevent timing attacks
        if not hmac.compare_digest(calculated_hash, check_hash):
            msg = "Data is NOT from Telegram"
            raise ValueError(msg)

        # Check if the authentication date is older than 24 hours (86400 seconds)
        if (time.time() - int(data.get("auth_date", 0))) > 86400:
            msg = "Data is outdated"
            raise ValueError(msg)

        return data

    async def __call__(self, data: LoginTelegramCommand) -> Token:
        self.check_telegram_authorization(
            auth_data=data.model_dump(exclude_unset=True),
            bot_token=self.bot_config.token.get_secret_value(),
        )

        user = await self.user_gateway.get_user_by_social_id(
            provider_name="telegram",
            provider_account_id=str(data.id),
        )

        if user:
            return self.security.create_token(user_id=user.id)

        async with self.uow:
            user = User(
                username=await self.user_service.generate_username(),
                role=UserRole.VISITOR,
                hashed_password=None,
                is_verified=False,
            )
            await self.user_gateway.add_user(user)
            social_id = SocialAccount(
                user_id=user.id,
                provider="telegram",
                provider_id=str(data.id),
            )
            await self.user_gateway.add_user_social_id(social_id)
            await self.uow.commit()
            return self.security.create_token(user_id=user.id)
