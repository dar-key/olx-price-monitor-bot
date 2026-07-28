import pytest

from src.bot.scraping.olx_parser import is_valid_olx_url


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://www.olx.kz/d/listing", True),
        ("https://olx.kz/search", True),
        ("https://sub.olx.kz/x", True),
        ("https://evil.com/?x=olx.kz", False),
        ("https://olx.kz.evil.com", False),
        ("ftp://olx.kz/x", False),
        ("not a url", False),
        ("javascript:alert(1)olx.kz", False),
        ("", False),
    ],
)
def test_is_valid_olx_url(url, expected):
    assert is_valid_olx_url(url) is expected
