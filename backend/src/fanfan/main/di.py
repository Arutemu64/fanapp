from dishka import AsyncContainer, Provider, make_async_container
from dishka.integrations.fastapi import FastapiProvider

from fanfan.main.db_config import DbConfigProvider
from fanfan.main.ioc.auth import OAuthProvider
from fanfan.main.ioc.bot import BotProvider
from fanfan.main.ioc.captcha import CaptchaProvider
from fanfan.main.ioc.config import ConfigProvider
from fanfan.main.ioc.cosplay2 import Cosplay2Provider
from fanfan.main.ioc.db import DbProvider, SqlGatewaysProvider
from fanfan.main.ioc.html import HtmlProvider
from fanfan.main.ioc.id_provider import SystemAuthProvider, WebAuthProvider
from fanfan.main.ioc.interactors import InteractorsProvider
from fanfan.main.ioc.jinja import JinjaProvider
from fanfan.main.ioc.mail import MailProvider
from fanfan.main.ioc.profanity import ProfanityProvider
from fanfan.main.ioc.push import PushProvider
from fanfan.main.ioc.redis import RedisProvider
from fanfan.main.ioc.security import SecurityProvider
from fanfan.main.ioc.serialization import SerializationProvider
from fanfan.main.ioc.services import ServicesProvider
from fanfan.main.ioc.stream import StreamProvider
from fanfan.main.ioc.sync import SyncProvider
from fanfan.main.ioc.tcloud import TCloudProvider


def get_common_providers() -> list[Provider]:
    return [
        ConfigProvider(),
        CaptchaProvider(),
        DbConfigProvider(),
        DbProvider(),
        InteractorsProvider(),
        BotProvider(),
        RedisProvider(),
        TCloudProvider(),
        SecurityProvider(),
        SerializationProvider(),
        ServicesProvider(),
        SqlGatewaysProvider(),
        StreamProvider(),
        SyncProvider(),
        Cosplay2Provider(),
        JinjaProvider(),
        HtmlProvider(),
        ProfanityProvider(),
        PushProvider(),
        MailProvider(),
        OAuthProvider(),
    ]


def create_web_container() -> AsyncContainer:
    providers = get_common_providers()
    providers += [FastapiProvider(), WebAuthProvider()]
    return make_async_container(*providers)


def create_system_container() -> AsyncContainer:
    providers = get_common_providers()
    providers += [SystemAuthProvider()]
    return make_async_container(*providers)
