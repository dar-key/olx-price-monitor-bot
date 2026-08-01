# OLX Price Monitor Telegram Bot

A Telegram bot that monitors OLX.kz listings and sends a notification whenever the price changes.

Built with **Python**, **aiogram 3**, **Playwright**, and **SQLite**. The bot periodically checks tracked listings in the background and supports multiple users.

> **Demo Bot**
>
> https://t.me/olx_monitor_temp_bot

---

## Demo

OLX Kazakhstan's primary audience is Russian-speaking, hence the bot's language.

### Add a listing

![Add listing](docs/demo-add.gif)

> user sends an olx link -> bot returns price and starts tracking this link

---

### Price change notification

![Price change](docs/price-change.gif)

> listing price changed -> notification with the new price

---

## Features

- Monitor multiple OLX.kz listings
- Automatic price checks every 15 minutes
- Telegram notifications on price changes
- Multi-user support
- SQLite storage
- Dynamic page scraping with Playwright
- Basic anti-bot handling using `playwright-stealth`
- Graceful shutdown
- Per-user tracking limit

---

## Commands

| Command                  | Description                 |
| ------------------------ | --------------------------- |
| `/start`                 | Start the bot               |
| `/list`                  | Show tracked listings       |
| `/delete <number>`       | Remove a listing            |
| `https://www.olx.kz/...` | Add a listing to monitoring |

---

## Installation

1. Clone the repository.

   ```bash
   git clone https://github.com/dar-key/olx-price-monitor-bot.git
   cd olx-price-monitor-bot
   ```

2. Install the dependencies.

   ```bash
   uv sync
   ```

3. Install Chromium.

   Linux

   ```bash
   uv run playwright install --with-deps chromium
   ```

   Windows

   ```bash
   uv run playwright install chromium
   ```

4. Copy the environment template to a new `.env` file and add your values:

   ```bash
   cp .env.example .env
   ```

5. Run the bot.

   ```bash
   uv run task start
   ```

### Running with Docker

```bash
cp .env.example .env
docker compose up --build
```

---

## Testing

```bash
uv sync
uv run pytest -v
uv run ruff check .
```

---

## Tech Stack

- Python 3.10+
- uv
- aiogram 3
- Playwright
- playwright-stealth
- aiosqlite (sqlite)
- pytest
