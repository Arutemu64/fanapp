from pathlib import Path
from typing import NewType

from jinja2 import Environment, FileSystemLoader

from fanfan.core.utils.pluralize import Plurals, pluralize

JinjaEnvironment = NewType("JinjaEnvironment", Environment)


def _plural(value: int, one: str, few: str, many: str) -> str:
    """`{{ n|plural('минуту', 'минуты', 'минут') }}`: the form for 1, 2-4, 5+."""
    return pluralize(value, Plurals(one, few, many))


def create_jinja_env() -> JinjaEnvironment:
    templates_path = Path(__file__).parent.joinpath("templates")
    environment = Environment(
        lstrip_blocks=True,
        trim_blocks=True,
        loader=FileSystemLoader(searchpath=templates_path),
        enable_async=True,
        autoescape=True,
    )
    environment.filters["plural"] = _plural
    return JinjaEnvironment(environment)
