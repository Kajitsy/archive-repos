# Anonka — Anonymous Telegram Messenger Bot

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![pyTelegramBotAPI](https://img.shields.io/badge/telebot-4.26.0-green.svg)](https://github.com/eternnoir/pyTelegramBotAPI)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)

**Anonka** is a feature-rich, privacy-focused Telegram bot designed for anonymous messaging. It generates a unique personal link for every registered user, allowing anyone to send anonymous messages, media, voice notes, stickers, and documents. It also supports bidirectional anonymous replies, interactive blacklist management, and customizable user settings.
The last commit was 19.05.2025

---

## 🌟 Key Features

- **Personal Anonymous Links**: Every user receives a unique shareable link (`https://t.me/<BOT_NAME>?start=<encoded_id>`). Senders can click the link and immediately begin sending anonymous messages without exposing their identity.
- **Two-Way Anonymous Replies**: Recipients can reply directly to any forwarded anonymous message using Telegram's native reply feature. The bot matches the message back to the original sender while keeping both identities masked.
- **Rich Media & Content Support**:
  - Text messages (with HTML styling support)
  - Photos & Videos (including media spoilers and message effects)
  - Voice messages & Video notes (round video messages)
  - Audio files & Documents
  - Stickers, Locations, and Contacts
- **Abuse Prevention & Stealth Blacklist**:
  - **One-Click Blocking**: Recipients can block any sender directly via the inline button attached to each message.
  - **Stealth Drop**: Blocked senders receive simulated success confirmations so they do not realize they have been blocked, preventing retaliation or workarounds.
  - **Blacklist Management**: Interactive paginated UI (`/blacklist`) to review blocked identifiers and unblock users at any time.
- **Double ID Masking**: Internal user IDs are obfuscated using multi-tier Base64 encoding to prevent reverse-engineering of user IDs through inline buttons and public links.
- **User Settings & Privacy Controls (`/settings`)**:
  - Toggle the inline "Block Sender" button on received messages.
  - Toggle automatic recipient reset after sending a message.
  - Allow or disallow anonymous replies to your messages.
- **User Statistics (`/me`)**:
  - Tracks total sent and received anonymous messages.
  - Displays registration date and personal link.
- **Resilient Polling Engine**:
  - Auto-reconnect loop handling Telegram API `FloodWait` (rate limits), SQLite concurrency/lock retries, and network errors.

---

## 📋 Bot Commands

| Command | Description |
| :--- | :--- |
| `/start` | View your personal anonymous link or bind a recipient if opened with parameters. |
| `/settings` | Open the interactive settings menu to customize bot behavior. |
| `/blacklist` | Open the paginated blacklist menu to inspect or unblock users. |
| `/me` | Display your account stats (messages sent/received, registration date). |

---

## ⚙️ Configuration

The bot is configured using environment variables:

| Variable | Required | Default | Description |
| :--- | :---: | :---: | :--- |
| `BOT_API_KEY` | **Yes** (in production) | — | Telegram Bot API token obtained from [@BotFather](https://t.me/BotFather). |
| `BOT_TESTING` | No | `0` | Set to `1` to enable test mode (uses `test_bot_data.db` and `TEST_BOT_API_KEY`). Set to `0` for production. |
| `TEST_BOT_API_KEY` | Conditional | — | Telegram Bot API token used when `BOT_TESTING=1`. |
| `PYTHONUNBUFFERED` | No | `1` | Forces unbuffered stdout and stderr streams for clean Docker logging. |

---

## 🚀 Quick Start & Deployment

### Option 1: Docker Compose (Recommended)

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd archive-repos
   ```

2. **Configure environment variables:**
   Edit [`docker-compose.yml`](docker-compose.yml) and insert your bot token:
   ```yaml
   services:
     bot:
       build: .
       volumes:
         - .:/app:z
       container_name: anonka
       restart: unless-stopped
       environment:
         - PYTHONUNBUFFERED=1
         - BOT_TESTING=0
         - BOT_API_KEY=YOUR_TELEGRAM_BOT_TOKEN_HERE
         - TEST_BOT_API_KEY=YOUR_TEST_TOKEN_OPTIONAL
   ```

3. **Start the bot container:**
   ```bash
   docker compose up -d --build
   ```

4. **View logs:**
   ```bash
   docker compose logs -f bot
   ```

5. **Stop the container:**
   ```bash
   docker compose down
   ```

---

### Option 2: Local Python Environment

1. **Prerequisites**: Python 3.11+ installed.

2. **Set up virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r req.txt
   ```

4. **Set environment variables and run:**
   ```bash
   export BOT_API_KEY="YOUR_TELEGRAM_BOT_TOKEN_HERE"
   export BOT_TESTING=0

   python main.py
   ```

---

## 🏗️ Project Architecture

```
.
├── Dockerfile              # Docker image definition (Python 3.11 base)
├── docker-compose.yml      # Docker Compose configuration and service definitions
├── main.py                 # Application entry point with fault-tolerant polling loop
├── req.txt                 # Python package dependencies
├── LICENSE                 # GNU General Public License v3.0
└── modules/
    ├── config.py           # Environment variables, bot instance initialization, config state
    ├── database.py         # SQLite database schema, connections, queries, and migrations
    ├── handlers.py         # Command handlers, message router, callbacks, and forwarding
    ├── ui.py               # Inline keyboards (settings, blacklist pagination) & message sender
    └── utils.py            # Base64 ID encoders/decoders and safe API call wrappers
```

### Database Schema (SQLite)

The bot automatically creates and manages an embedded SQLite database (`bot_data.db` or `test_bot_data.db`):

- **`users`**: Stores user metadata, first/last name, username, registration timestamp, message counters (`messages_sent`, `messages_received`), and obfuscated IDs.
- **`user_targets`**: Maps the active recipient selection for senders (`sender_id` $\rightarrow$ `target_id`).
- **`blacklists`**: Stores blocked relationships (`blocker_id`, `blocked_id`, `blocked_at`, `last_message_at`).
- **`reply_links`**: Stores the mapping between delivered messages and original anonymous senders to power bidirectional replies.
- **`user_settings`**: Stores per-user feature flags (`blacklist_enabled`, `reset_recipient`, `answers`).

---

## 📄 License

This project is licensed under the terms of the [GNU General Public License v3.0](LICENSE).
