import traceback
import telebot
from telebot import types
from modules.config import bot, ENTRIES_PER_BLACKLIST_PAGE
import modules.database as db
import modules.utils as utils

def create_settings_keyboard(settings, user_id_encoded):
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton(
            f"Кнопка блокировки: {'✅ Вкл' if settings['blacklist_enabled'] else '❌ Выкл'}",
            callback_data=f"toggle_blacklist_{user_id_encoded}"
        ),
        types.InlineKeyboardButton(
            f"Сброс получателя: {'✅ Да' if settings['reset_recipient'] else '❌ Нет'}",
            callback_data=f"toggle_reset_{user_id_encoded}"
        ),
        types.InlineKeyboardButton(
            f"Ответы на анонимки: {'✅ Вкл' if settings['answers'] else '❌ Выкл'}",
            callback_data=f"toggle_answers_{user_id_encoded}"
        )
    )
    return keyboard

def send_blacklist_page(chat_id, message_id, encoded_user_id, page, is_edit=True):
    """Sends or edits a message displaying a paginated blacklist."""
    blacklist_entries = db.get_blacklist(encoded_user_id)
    total_entries = len(blacklist_entries)

    if not total_entries:
        empty_text = "Ваш черный список пуст."
        if is_edit:
            utils.safe_edit_text(empty_text, chat_id=chat_id, message_id=message_id, reply_markup=None)
        else:
            utils.safe_send(chat_id, empty_text)
        return

    total_pages = (total_entries + ENTRIES_PER_BLACKLIST_PAGE - 1) // ENTRIES_PER_BLACKLIST_PAGE
    page = max(0, min(page, total_pages - 1)) # Ensure page is within valid bounds

    start_index = page * ENTRIES_PER_BLACKLIST_PAGE
    current_page_entries = blacklist_entries[start_index : start_index + ENTRIES_PER_BLACKLIST_PAGE]

    text = f"<b>Черный список</b> (Страница {page + 1}/{total_pages}):\n\n"
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    buttons = []

    for i, entry in enumerate(current_page_entries, start=1):
        global_index = start_index + i
        blocked_id_display = entry['blocked_id'][:8] + '...' # Show only part of the ID
        text += f"{global_index}. <code>{blocked_id_display}</code>"
        details = []
        if entry['blocked_at']: details.append(f"С {entry['blocked_at']}")
        if entry['last_message_at']: details.append(f"Посл.поп: {entry['last_message_at']}")
        if details: text += f"\n   <i>({', '.join(details)})</i>"
        text += "\n"
        # Pass the full blocked_id and current page for callback
        buttons.append(types.InlineKeyboardButton(
            f"Разбл. {global_index}",
            callback_data=f"unblock_{entry['blocked_id']}_{page}"
        ))

    if buttons: keyboard.add(*buttons) # Add unblock buttons

    # Navigation buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(types.InlineKeyboardButton("⬅️ Пред.", callback_data=f"blacklist_prev_{page}"))
    if (page + 1) * ENTRIES_PER_BLACKLIST_PAGE < total_entries:
        nav_buttons.append(types.InlineKeyboardButton("След. ➡️", callback_data=f"blacklist_next_{page}"))
    if nav_buttons: keyboard.row(*nav_buttons) # Add navigation buttons in a new row

    # Send or Edit the message
    if is_edit:
        utils.safe_edit_text(text, chat_id=chat_id, message_id=message_id, reply_markup=keyboard, parse_mode='HTML')
    else:
        # If not editing, we need to send a new message. message_id isn't relevant here.
        utils.safe_send(chat_id, text, reply_markup=keyboard, parse_mode='HTML')


def send_anonymous_message(target_chat_id, message, markup, message_prefix, original_sender_encoded, target_encoded_id):
    """
    Forwards the user's message anonymously to the target chat.
    Handles various content types and potential API errors.
    Returns (bool: success, str: error_message_for_sender | None).
    """
    message: telebot.types.Message = message
    bot_message = None
    bot_message2 = None # For voice/sticker caption separation
    caption_prefix = f"<b>{message_prefix}</b>"

    try:
        content_type = message.content_type
        args = {'chat_id': target_chat_id, 'reply_markup': markup, 'parse_mode': 'HTML'}
        caption = getattr(message, 'caption', None) or getattr(message, 'text', None) or ''

        # Handle message effects if present
        if hasattr(message, 'effect_id') and message.effect_id in [
            '5107584321108051014', '5104858069142078462', '5159385139981059251',
            '5104841245755180586', '5046509860389126442', '5046589136895476101'
        ]:
            args['message_effect_id'] = message.effect_id

        # --- Content Type Specific Handling ---
        if content_type == 'text':
            args['text'] = f"{caption_prefix}:\n{caption}"
            bot_message = bot.send_message(**args)

        elif content_type == 'photo':
            file_id = message.photo[-1].file_id
            args['photo'] = file_id
            args['caption'] = f"{caption_prefix}:\n{caption}"
            args['has_spoiler'] = getattr(message, 'has_media_spoiler', False)
            bot_message = bot.send_photo(**args)

        elif content_type == 'video':
            file_id = message.video.file_id
            args['video'] = file_id
            args['caption'] = f"{caption_prefix}:\n{caption}"
            args['has_spoiler'] = getattr(message, 'has_media_spoiler', False)
            bot_message = bot.send_video(**args)

        elif content_type == 'audio':
            file_id = message.audio.file_id
            args['audio'] = file_id
            args['caption'] = f"{caption_prefix}:\n{caption}"
            bot_message = bot.send_audio(**args)

        elif content_type == 'document':
            file_id = message.document.file_id
            args['document'] = file_id
            args['caption'] = f"{caption_prefix}:\n{caption}"
            bot_message = bot.send_document(**args)

        elif content_type == 'voice':
            file_id = message.voice.file_id
            args['voice'] = file_id
            bot_message2 = utils.safe_send(target_chat_id, f"{caption_prefix}:")
            bot_message = bot.send_voice(**args)

        elif content_type == 'video_note':
            file_id = message.video_note.file_id
            args['video_note'] = file_id
            bot_message2 = utils.safe_send(target_chat_id, f"{caption_prefix}:")
            bot_message = bot.send_video_note(**args)

        elif content_type == 'sticker':
            file_id = message.sticker.file_id
            args['sticker'] = file_id
            del args['parse_mode']
            bot_message2 = utils.safe_send(target_chat_id, f"{caption_prefix}:")
            bot_message = bot.send_sticker(**args)
            
        elif content_type == 'location':
            latitude = message.location.latitude
            longitude = message.location.longitude
            args['latitude'] = latitude
            args['longitude'] = longitude
            del args['parse_mode']
            bot_message2 = utils.safe_send(target_chat_id, f"{caption_prefix}:")
            bot_message = bot.send_location(**args)

        elif content_type == 'contact':
            phone_number = message.contact.phone_number
            first_name = message.contact.first_name
            last_name = message.contact.last_name or ''
            args['phone_number'] = phone_number
            args['first_name'] = first_name
            args['last_name'] = last_name
            del args['parse_mode']
            bot_message2 = utils.safe_send(target_chat_id, f"{caption_prefix}:")
            bot_message = bot.send_contact(**args)

        else:
            print(f"Unsupported message type: {content_type}")
            return False, "Тип сообщения не поддерживается."

        # --- Link message ID to original sender ---
        if bot_message:
            db.add_reply_link(target_encoded_id, bot_message.message_id, original_sender_encoded)
        if bot_message2: # Also link the separate caption message if it exists
             db.add_reply_link(target_encoded_id, bot_message2.message_id, original_sender_encoded)

        return True, None # Success

    except telebot.apihelper.ApiTelegramException as e:
        error_message = f"API Error sending to {target_chat_id}: {e}"
        print(error_message)
        user_facing_error = "Не удалось доставить сообщение."
        if "bot was blocked by the user" in str(e) or "user is deactivated" in str(e):
             user_facing_error += " Получатель заблокировал бота или его аккаунт неактивен."
        elif "chat not found" in str(e):
             user_facing_error += " Чат получателя не найден."
        # Add more specific error handling if needed
        return False, user_facing_error
    except Exception as e:
        error_message = f"Unexpected error sending message type {content_type}: {e}"
        print(error_message)
        traceback.print_exc()
        return False, "Произошла внутренняя ошибка при отправке сообщения."