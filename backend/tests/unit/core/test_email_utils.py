import pytest

from fanfan.core.services.email_login import EMAIL_OTP_LENGTH, generate_numeric_code
from fanfan.core.utils.email import normalize_email

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("User@Example.com", "user@example.com"),
        ("  trailing@space.com  ", "trailing@space.com"),
        ("already@normal.com", "already@normal.com"),
        ("MiXeD.CaSe@Domain.RU", "mixed.case@domain.ru"),
    ],
)
def test_normalize_email(raw: str, expected: str):
    assert normalize_email(raw) == expected


def test_generate_numeric_code_is_zero_padded_digits():
    for _ in range(50):
        code = generate_numeric_code()
        assert len(code) == EMAIL_OTP_LENGTH
        assert code.isdigit()


def test_generate_numeric_code_varies():
    codes = {generate_numeric_code() for _ in range(50)}

    # Practically impossible to draw 50 identical 6-digit codes.
    assert len(codes) > 1
