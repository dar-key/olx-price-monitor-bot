from src.bot.services.formatting import price_change_message


def test_price_change_message_escapes_html():
    msg = price_change_message("<b>1000</b>", "1200", "https://olx.kz/x")
    assert "&lt;b&gt;" in msg
    assert "<b>1000</b>" not in msg  # raw tag must not survive


def test_price_change_message_contains_new_price():
    msg = price_change_message("1000", "1200 тг.", "https://olx.kz/x")
    assert "1200" in msg


def test_price_change_message_contains_link():
    msg = price_change_message("1000", "1200", "https://olx.kz/x")
    assert "https://olx.kz/x" in msg
