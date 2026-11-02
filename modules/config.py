import telebot
import os
import sys

ENTRIES_PER_BLACKLIST_PAGE = 5
testing = True if os.getenv("BOT_TESTING") == "1" else False

if testing:
    DB_FILE = "test_bot_data.db"
    TOKEN = os.getenv("TEST_BOT_API_KEY")
else:
    DB_FILE = "bot_data.db"
    TOKEN = os.getenv("BOT_API_KEY")

# --- Initialize bot instance using the loaded TOKEN ---
try:
    bot = telebot.TeleBot(TOKEN, parse_mode='HTML')
    bot_info = bot.get_me()
    BOT_NAME = bot_info.username
    print(f"Successfully connected to bot: {BOT_NAME}")
except Exception as e:
    print(f"Error initializing Telegram Bot with the provided TOKEN: {e}")
    print("Please ensure the TOKEN in bot.txt is correct and valid.")
    sys.exit(1)


print(f"--- Configuration ---")
print(f"Bot Name:   {BOT_NAME}")
print(f"Testing:    {testing}")
print(f"Database:   {DB_FILE}")
print(f"---------------------")
