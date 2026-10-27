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


@pytest.mark.parametrize(
    ("minutes_ahead", "expected"),
    [
        (1, ", примерно 1 минута"),
        (7, ", примерно 7 минут"),
        (60, ", примерно 1 час"),
        (65, ", примерно 1 час 5 минут"),
        (None, ""),
    ],
)
async def test_subscription_reminder_writes_the_wait_as_the_screen_does(
    minutes_ahead: int | None, expected: str
) -> None:
    renderer = JinjaTemplateRenderer(create_jinja_env())
    context = {
        "kind": "soon",
        "event_number": 7,
        "event_title": "Акт",
        "positions_ahead": 3,
        "minutes_ahead": minutes_ahead,
        "reason_msg": None,
    }

    body = await renderer.render("subscription_notification.jinja2", context)

    assert body == (
        "До выступления <b>№007 «Акт»</b> осталось <b>3 выступления</b>" + expected
    )
