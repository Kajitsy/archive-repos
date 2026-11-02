import base64
from datetime import datetime
import telebot
from modules.config import bot

# --- Encoding/Decoding ---
def _safe_b64_encode(data_str):
    return base64.urlsafe_b64encode(data_str.encode()).decode().rstrip("=")

def _safe_b64_decode(encoded_str):
    try:
        padding = '=' * (4 - len(encoded_str) % 4)
        return base64.urlsafe_b64decode(encoded_str + padding).decode()
    except Exception:
        print(f"Error decoding Base64 string: {encoded_str}")
        return None

def one_encode_user_id(user_id):
    return _safe_b64_encode(str(user_id))

def two_encode_user_id(user_id):
    encoded_once = _safe_b64_encode(str(user_id))
    return _safe_b64_encode(encoded_once) if encoded_once else None

def decode_user_id_to_int(encoded_id):
    decoded = _safe_b64_decode(encoded_id)
    try:
        return int(decoded) if decoded else None
    except (ValueError, TypeError):
        print(f"Error converting decoded string to int: {decoded}")
        return None

# --- Time Utility ---
def get_current_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# --- Safe Telegram API Call Wrappers ---
def safe_reply(message, text, **kwargs):
    try:
        bot.reply_to(message, text, **kwargs)
    except Exception as e:
        print(f"Error replying to message {message.message_id} in chat {message.chat.id}: {e}")

def safe_send(chat_id, text, **kwargs):
    try:
        return bot.send_message(chat_id, text, **kwargs)
    except Exception as e:
        print(f"Error sending to chat {chat_id}: {e}")
        return None

def safe_edit_markup(chat_id, message_id, reply_markup=None):
     try:
         bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=reply_markup)
     except telebot.apihelper.ApiTelegramException as e:
         if "message is not modified" not in str(e) and \
            "message can't be edited" not in str(e) and \
            "message to edit not found" not in str(e):
              print(f"Error editing markup for msg {message_id} in chat {chat_id}: {e}")
     except Exception as e:
         print(f"Unexpected error editing markup for msg {message_id} in chat {chat_id}: {e}")

def safe_edit_text(text, chat_id, message_id, **kwargs):
    try:
        bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, **kwargs)
    except telebot.apihelper.ApiTelegramException as e:
        if "message is not modified" not in str(e) and \
           "message to edit not found" not in str(e):
            print(f"Error editing text for msg {message_id} in chat {chat_id}: {e}")
    except Exception as e:
        print(f"Unexpected error editing text for msg {message_id} in chat {chat_id}: {e}")

def safe_answer_callback(call, text="", show_alert=False):
    try:
        bot.answer_callback_query(call.id, text=text, show_alert=show_alert)
    except Exception as e:
        print(f"Error answering callback {call.id}: {e}")