from dishka import AsyncContainer, Provider, make_async_container
from dishka.integrations.fastapi import FastapiProvider

from fanfan.main.ioc.auth import AuthProvider
from fanfan.main.ioc.bot import BotProvider
from fanfan.main.ioc.config import ConfigProvider
from fanfan.main.ioc.cosplay2 import Cosplay2Provider
from fanfan.main.ioc.db import DbProvider
from fanfan.main.ioc.gateways import GatewaysProvider
from fanfan.main.ioc.id_provider import (
    JwtTokenProcessorProvider,
    SystemAuthProvider,
    WebAuthProvider,
)
from fanfan.main.ioc.interactors import InteractorsProvider
from fanfan.main.ioc.jinja import JinjaProvider
from fanfan.main.ioc.mail import MailProvider
from fanfan.main.ioc.push import PushProvider
from fanfan.main.ioc.redis import RedisProvider
from fanfan.main.ioc.services import ServicesProvider
from fanfan.main.ioc.stream import StreamProvider
from fanfan.main.ioc.tcloud import TCloudProvider


def get_common_providers() -> list[Provider]:
    return [
        ConfigProvider(),
        JwtTokenProcessorProvider(),
        DbProvider(),
        InteractorsProvider(),
        BotProvider(),
        RedisProvider(),
        TCloudProvider(),
        ServicesProvider(),
        GatewaysProvider(),
        StreamProvider(),
        Cosplay2Provider(),
        JinjaProvider(),
        PushProvider(),
        MailProvider(),
        AuthProvider(),
    ]


def create_web_container() -> AsyncContainer:
    providers = get_common_providers()
    providers += [FastapiProvider(), WebAuthProvider()]
    return make_async_container(*providers)


def create_system_container() -> AsyncContainer:
    providers = get_common_providers()
    providers += [SystemAuthProvider()]
    return make_async_container(*providers)
