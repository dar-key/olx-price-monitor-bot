# OLX Price Monitor Telegram Bot

A Telegram bot that monitors OLX.kz listings and sends a notification whenever the price changes.

Built with **Python**, **aiogram 3**, **Playwright**, and **SQLite**. The bot periodically checks tracked listings in the background and supports multiple users.

> **Demo Bot**
>
> https://t.me/olx_monitor_temp_bot

---

## Demo

### Add a listing

![Add listing](docs/demo-add.gif)

---

### Price change notification

![Price change](docs/price-change.gif)

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

Clone the repository.

```bash
git clone https://github.com/dar-key/olx-monitor-telegram-bot.git
cd olx-monitor-telegram-bot
```

Create a virtual environment.

```bash
python -m venv .venv
```

Activate it.

Linux / macOS

```bash
source .venv/bin/activate
```

Windows

```powershell
.venv\Scripts\activate
```

Install dependencies.

```bash
pip install -r requirements.txt
```

Create a `.env` file.

```env
BOT_TOKEN=your_bot_token
```

Install Chromium.

```bash
playwright install chromium
```

Run the bot.

```bash
python bot.py
```

---

## Deploying on Linux

When deploying to a fresh Ubuntu or Debian server, Chromium may require additional system libraries.

Install Chromium together with its dependencies:

```bash
playwright install --with-deps chromium
```

---

## Tech Stack

- Python 3.11+
- aiogram 3
- Playwright
- playwright-stealth
- SQLite
- python-dotenv

---

## License

MIT
