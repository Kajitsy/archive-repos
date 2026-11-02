# Telegram Collectible Card Game Bot

A multi-chat Telegram bot written in Python that allows group communities to create, manage, and collect custom digital trading cards with rarity tiers, points, and cooldown mechanics.
The last commit was 19.05.2025

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Rarity System & Scoring](#rarity-system--scoring)
- [File Structure & Data Storage](#file-structure--data-storage)
- [Prerequisites](#prerequisites)
- [Installation & Setup](#installation--setup)
- [Telegram BotFather Configuration](#telegram-botfather-configuration)
- [Administration & Usage Guide](#administration--usage-guide)
  - [Adding the Bot to a Group](#adding-the-bot-to-a-group)
  - [Admin Control Panel](#admin-control-panel)
  - [Card Management](#card-management)
  - [Admin Management](#admin-management)
  - [Cooldown & Trigger Word](#cooldown--trigger-word)
  - [Player Experience](#player-experience)
- [License](#license)

---

## Overview

This bot introduces a gacha/collectible card minigame to Telegram group chats. Each group operates independently with its own:
- Dedicated card deck and custom images.
- Rarity distribution and drop rates.
- Cooldown timer between card draws.
- Custom trigger word (e.g., `карта`, `card`, `loot`).
- Leaderboards and user card collection history.

Group administrators manage their chat's pool of cards and settings in private messages with the bot via interactive inline keyboards.

---

## Key Features

- **Multi-Group Isolation:** Every group chat maintains its own independent card pool, user statistics, admin list, and cooldown rules.
- **Custom Card Uploads:** Administrators can add custom cards by sending photos directly to the bot in private messages, assigning names and rarity tiers.
- **Visual Card Gallery & Deletion:** Interactive, paginated card deletion interface showing photo media groups and inline buttons.
- **Weighted RNG Drops:** Cards are awarded based on realistic drop probabilities across 4 rarity tiers.
- **Collection & Duplicates Tracking:** The bot keeps track of each player's acquired cards and points, notifying users when they receive a new card or pull a duplicate.
- **Spam Protection (Cooldown):** Chat admins can configure a cooldown interval (`HH:MM:SS`) to control how often members can pull cards.
- **Custom Trigger Word:** Configurable chat trigger word that activates card pulls in the group (defaults to `карта`).
- **Admin Delegation:** Group admins can grant or revoke bot management permissions for other members by forwarding their messages.

---

## Rarity System & Scoring

When a player triggers a card draw, the bot rolls for a rarity tier based on weighted probabilities:

| Rarity (Internal Key) | Russian Display | Drop Chance | Points Awarded |
| :--- | :--- | :---: | :---: |
| **Common** (`обычная`) | Обычная | **70%** | **10** |
| **Rare** (`редкая`) | Редкая | **20%** | **50** |
| **Mythic** (`мифическая`) | Мифическая | **8%** | **200** |
| **Legendary** (`легендарная`) | Легендарная | **2%** | **500** |

If a rolled rarity tier contains no cards in the chat's pool, the bot informs the player that no cards of that tier have been added yet by administrators.

---

## File Structure & Data Storage

```text
.
├── main.py                   # Main bot logic, handlers, and event loops
├── chats_settings.json       # Stores per-group settings, card pools, user stats, and admin IDs
├── photo_id_mapping.json     # Maps short MD5 hashes to Telegram photo file IDs
├── users_data.json           # Maps user IDs to group chats where they have admin privileges
├── user_cooldowns.json       # Tracks timestamps of card draws per user per chat
├── LICENSE                   # GNU General Public License v3.0
└── README.md                 # Project documentation
```

### Data Files Explained

- **`chats_settings.json`**: Contains configuration for each chat ID: group name, admin user IDs, custom trigger word, cooldown configuration (`hours`, `minutes`, `seconds`), card definitions grouped by rarity, and user collections.
- **`photo_id_mapping.json`**: Caches 10-character MD5 hashes of Telegram `file_id` strings, keeping payload sizes small in callback queries and JSON databases.
- **`users_data.json`**: Stores references to which groups a user can administer, enabling multi-chat management through `/settings` in DM.
- **`user_cooldowns.json`**: Persists next-available draw timestamps to prevent bot restart exploits.

---

## Prerequisites

- **Python 3.8+**
- A Telegram bot token from [@BotFather](https://t.me/BotFather)

---

## Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/archive-repos.git
   cd archive-repos
   ```

2. **Create and activate a virtual environment (recommended):**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   The bot uses `pyTelegramBotAPI`:
   ```bash
   pip install pyTelegramBotAPI
   ```

4. **Initialize JSON storage files:**
   Ensure valid empty JSON files exist before the initial launch:
   ```bash
   echo "{}" > photo_id_mapping.json
   echo "{}" > users_data.json
   echo "{}" > chats_settings.json
   echo "{}" > user_cooldowns.json
   ```

5. **Configure your Telegram Bot Token:**
   Open `main.py` and replace the placeholder tokens with your Telegram bot token:
   ```python
   MAIN_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"
   TEST_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"
   testing = False  # Set to True if using TEST_TOKEN
   ```

6. **Run the bot:**
   ```bash
   python main.py
   ```

---

## Telegram BotFather Configuration

To ensure smooth group operation, configure the following in [@BotFather](https://t.me/BotFather):

1. **Disable Group Privacy (Recommended):**
   - Send `/setprivacy` to `@BotFather`.
   - Select your bot.
   - Choose **Disable**.
   - *Why:* This allows the bot to detect the trigger word (e.g., `карта`) without requiring members to tag the bot directly.
   - *Alternative:* If privacy mode remains enabled, the bot must either be promoted to group Administrator with "Read all group messages" permissions, or users must address the bot directly.

2. **Allow Adding to Groups:**
   - Send `/setjoingroups` to `@BotFather`.
   - Ensure it is set to **Enable**.

---

## Administration & Usage Guide

### Adding the Bot to a Group

1. Invite the bot into your Telegram group or click the **"Добавить бота в группу"** (Add bot to group) button in a private chat with the bot (`/start`).
2. When added, the bot automatically initializes the chat in `chats_settings.json` and registers the group's administrators.

### Admin Control Panel

- In the group chat, an administrator can send `/settings`. The bot replies with a button linking directly to private messages: `https://t.me/<bot_username>?start=settings_<chat_id>`.
- In private messages with the bot, sending `/settings` displays a list of all groups you manage.
- Selecting a group opens the **Chat Control Panel**:
  - **Карточки (Cards):** Add or remove cards.
  - **Администраторы (Administrators):** Manage bot administrators for the group.
  - **Задержка (Cooldown):** Configure card draw cooldown.
  - **Триггерное слово (Trigger Word):** Change the word used to roll cards.

### Card Management

- **Adding a Card:**
  1. Click **Карточки** > **Добавить карточку**.
  2. Select the rarity tier: *Обычная (Common)*, *Редкая (Rare)*, *Мифическая (Mythic)*, or *Легендарная (Legendary)*.
  3. Send an image/photo to the bot.
  4. If the photo has a caption, it is used as the card name. If not, the bot will prompt you to reply with the card's name.
- **Removing a Card:**
  1. Click **Карточки** > **Удалить карточку**.
  2. Select the rarity tier.
  3. Browse the paginated photo gallery with previous/next page navigation.
  4. Click the corresponding card button to delete it from the chat pool.

### Admin Management

- **Add an Admin:** Click **Администраторы** > **Добавить администратора** and forward any message from the desired user.
- **Remove an Admin:** Click **Администраторы** > **Удалить администратора** and forward a message from the user to revoke. (Note: A chat must always have at least one administrator).

### Cooldown & Trigger Word

- **Cooldown:** Set how frequently users can request a card by sending time in `HH:MM:SS` format (e.g., `00:05:00` for 5 minutes, `01:00:00` for 1 hour).
- **Trigger Word:** Send the desired word or phrase (e.g., `card`, `loot`, `карта`). Any message matching this text in the group will trigger a roll.

### Player Experience

1. A member sends the trigger word (e.g., `карта`) in the group.
2. If the user is currently on cooldown, the bot reports the remaining wait time in seconds.
3. If off cooldown:
   - A random rarity tier is selected according to drop rates.
   - A random card from that rarity pool is chosen.
   - The user is awarded points corresponding to the card's tier.
   - The card is added to the user's collection (or marked as duplicate if already owned).
   - The bot replies with the card image, rarity badge, points gained, and total points.

---

## License

This project is licensed under the [GNU General Public License v3.0](LICENSE).
