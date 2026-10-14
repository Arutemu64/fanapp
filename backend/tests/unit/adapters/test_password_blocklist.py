import pytest

from fanfan.adapters.auth.password_blocklist import WordListPasswordBlocklist

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def blocklist() -> WordListPasswordBlocklist:
    return WordListPasswordBlocklist()


@pytest.mark.parametrize("password", ["1234567890", "qwertyuiop", "PASSWORD123"])
def test_blocks_common_passwords_case_insensitively(
    blocklist: WordListPasswordBlocklist, password: str
) -> None:
    assert blocklist.is_blocked(password) is True


@pytest.mark.parametrize(
    "password",
    [
        "correct horse battery staple",
        # A blocklisted word inside a longer password is fine: the whole
        # password is compared, never its substrings.
        "1234567890-and-then-some-more",
    ],
)
def test_allows_everything_else(
    blocklist: WordListPasswordBlocklist, password: str
) -> None:
    assert blocklist.is_blocked(password) is False
