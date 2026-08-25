from pathlib import Path
from typing import NewType

from jinja2 import Environment, FileSystemLoader

JinjaEnvironment = NewType("JinjaEnvironment", Environment)


def create_jinja_env() -> JinjaEnvironment:
    templates_path = Path(__file__).parent.joinpath("templates")
    environment = Environment(
        lstrip_blocks=True,
        trim_blocks=True,
        loader=FileSystemLoader(searchpath=templates_path),
        enable_async=True,
        autoescape=True,
    )
    return JinjaEnvironment(environment)
