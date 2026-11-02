import time
import traceback
import requests
import sqlite3
import telebot

from modules.config import bot, BOT_NAME
import modules.database as db
import modules.handlers as handlers

if __name__ == "__main__":
    print("Initializing database...")
    db.init_db()

    print("Registering handlers...")
    handlers.register_handlers()

    print(f"Starting bot ({BOT_NAME})...")
    while True:
        try:
            print("Bot polling started...")
            bot.polling(none_stop=True, interval=0, timeout=40)
        except sqlite3.Error as sql_err:
             print(f"!!! MAIN LOOP: SQLite Error: {sql_err} !!!")
             traceback.print_exc()
             print("Restarting bot polling due to DB error in 5 seconds...")
             time.sleep(5)
        except telebot.apihelper.ApiTelegramException as tg_err:
            print(f"!!! MAIN LOOP: Telegram API Error: {tg_err} !!!")
            wait_time = 10 # Default wait
            if 'FloodWait' in str(tg_err) or 'Too Many Requests' in str(tg_err):
                try:
                    wait_time_str = str(tg_err).split('retry in ')[-1].split(' ')[0]
                    wait_time = int(wait_time_str) + 2
                    print(f"Flood/Rate limit detected. Waiting for {wait_time} seconds...")
                except Exception as parse_e:
                    print(f"Could not parse wait time ({parse_e}). Waiting 60 seconds...")
                    wait_time = 60
            else:
                 traceback.print_exc()
            print(f"Restarting bot polling due to Telegram API error in {wait_time} seconds...")
            time.sleep(wait_time)
        except requests.exceptions.RequestException as req_err:
             print(f"!!! MAIN LOOP: Network error: {req_err} !!!")
             traceback.print_exc()
             print("Restarting bot polling due to network error in 15 seconds...")
             time.sleep(15)
        except Exception as e:
            print(f"!!! MAIN LOOP: An unexpected error occurred: {e} !!!")
            traceback.print_exc()
            print("Restarting bot polling in 20 seconds...")
            time.sleep(20)
        finally:
            print("Bot polling loop finished or crashed. Restarting...")
            time.sleep(1)