import html


def esc(value: str) -> str:
    return html.escape(str(value))


def price_change_message(old_price: str, new_price: str, url: str) -> str:
    return (
        f"<b>Изменение цены на OLX!</b>\n\n"
        f"Старая цена: <s>{esc(old_price)}</s>\n"
        f"Новая цена: <b>{esc(new_price)}</b>\n\n"
        f"<a href='{esc(url)}'>Ссылка на объявление</a>"
    )


def monitor_added_message(price: str) -> str:
    return (
        f"<b>Товар добавлен на мониторинг!</b>\n\n"
        f"<b>Текущая цена:</b> {esc(price)}\n\n"
        f"Я буду периодически проверять её и пришлю уведомление, если она изменится."
    )


def monitor_limit_reached_message(max_count: int, price: str) -> str:
    return (
        f"Не удалось добавить товар на мониторинг. "
        f"Лимит исчерпан: отслеживаются {max_count} объявлений.\n\n"
        f"<b>Текущая цена:</b> {esc(price)}"
    )
