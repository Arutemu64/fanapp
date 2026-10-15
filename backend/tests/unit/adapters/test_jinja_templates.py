import pytest

from fanfan.adapters.jinja.factory import create_jinja_env
from fanfan.adapters.jinja.renderer import JinjaTemplateRenderer

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("count", "expected"),
    [(1, "1 минуту"), (3, "3 минуты"), (5, "5 минут"), (12, "12 минут")],
)
def test_plural_filter_picks_the_russian_form(count: int, expected: str) -> None:
    template = create_jinja_env().from_string(
        "{{ n }} {{ n|plural('минуту', 'минуты', 'минут') }}"
    )

    assert template.render(n=count) == expected


async def test_editor_notification_escapes_the_reason() -> None:
    # The reason is plain text (it is also the mailing summary), so an event title
    # carrying markup must reach the HTML body escaped, not as tags.
    renderer = JinjaTemplateRenderer(create_jinja_env())

    body = await renderer.render(
        "schedule_change_editor.jinja2",
        {"editor_username": "org", "reason_msg": "Выступление «<b>» перенесено"},
    )

    assert (
        body == "@org сделал изменение в программе: Выступление «&lt;b&gt;» перенесено"
    )


async def test_login_email_names_the_expiry_in_the_right_form() -> None:
    renderer = JinjaTemplateRenderer(create_jinja_env())
    context = {"username": "Аня", "login_code": "123456", "expires_in_minutes": 2}

    text = await renderer.render("email_login_code.txt.jinja2", context)

    assert "Код действует 2 минуты." in text
