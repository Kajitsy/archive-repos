from telebot import types
from modules.config import bot, BOT_NAME
import modules.database as db
import modules.utils as utils
import modules.ui as ui

def register_handlers():
    # --- Command Handlers ---
    @bot.message_handler(commands=['start'])
    def handle_start(message: types.Message):
        user = message.from_user
        sender_encoded_id, _ = db.update_user_data(user)
        if not sender_encoded_id:
            utils.safe_reply(message, "Произошла ошибка при обработке вашего ID.")
            return

        args = message.text.split()
        target_encoded_arg = args[1] if len(args) > 1 else None

        if target_encoded_arg:
            target_id_int = utils.decode_user_id_to_int(target_encoded_arg)

            if target_id_int is None:
                utils.safe_reply(message, "Неверная ссылка. Пожалуйста, используйте правильную ссылку.")
                return

            if target_id_int == user.id:
                utils.safe_reply(message, "Самому себе писать анонимки - это странно 🤨\n"
                                f"Твоя ссылка для получения сообщений: https://t.me/{BOT_NAME}?start={sender_encoded_id}")
                # Clear any potentially previously set target
                db.set_user_target(sender_encoded_id, None)
                return

            db.set_user_target(sender_encoded_id, target_encoded_arg)
            utils.safe_reply(message, f"✅ Получатель установлен. Ваше следующее сообщение будет отправлено анонимно.") # Add target name later if desired

        else:
            utils.safe_reply(message,
                 f"👋 Привет, <b>{user.first_name}</b>!\n\nЯ помогу отправить анонимное сообщение.\n\n"
                 f"🔗 Твоя персональная ссылка для получения сообщений:\n<code>https://t.me/{BOT_NAME}?start={sender_encoded_id}</code>\n\n"
                 f"<i>Отправь эту ссылку друзьям, чтобы они могли написать тебе анонимно!</i>\n\n"
                 f"Чтобы отправить кому-то сообщение, перейди по <b>его</b> ссылке.")
            db.set_user_target(sender_encoded_id, None)


    @bot.message_handler(commands=['settings'])
    def handle_settings(message: types.Message):
        sender_encoded_id, _ = db.update_user_data(message.from_user)
        if not sender_encoded_id: return
        settings = db.get_user_settings(sender_encoded_id)
        keyboard = ui.create_settings_keyboard(settings, sender_encoded_id)
        utils.safe_reply(message, "⚙️ <b>Настройки:</b>", reply_markup=keyboard)

    @bot.message_handler(commands=['blacklist'])
    def handle_blacklist(message: types.Message):
        sender_encoded_id, _ = db.update_user_data(message.from_user)
        if not sender_encoded_id: return
        ui.send_blacklist_page(message.chat.id, message.message_id, sender_encoded_id, page=0, is_edit=False)
        
    @bot.message_handler(commands=['me'])
    def handle_me(message: types.Message):
        sender_encoded_id, _ = db.update_user_data(message.from_user)
        if not sender_encoded_id: return
        sent = db.get_message_count(sender_encoded_id, sent=True)
        received = db.get_message_count(sender_encoded_id, sent=False)
        utils.safe_reply(message, 
            f"📊 <b>Ваша статистика:</b>\n\n"
            f"📤 Отправлено анонимок: {sent}\n"
            f"📥 Получено анонимок: {received}\n"
            f"✏️ Дата регистрации: {db.get_user_registration_date(sender_encoded_id)}\n\n"
            f"🔗 Ваша ссылка для получения сообщений:\n<code>https://t.me/{BOT_NAME}?start={sender_encoded_id}</code>\n\n")


    # --- Callback Query Handlers ---
    @bot.callback_query_handler(func=lambda call: call.data.startswith("toggle_"))
    def handle_toggle_settings(call: types.CallbackQuery):
        sender_encoded_id, _ = db.update_user_data(call.from_user)
        if not sender_encoded_id:
            utils.safe_answer_callback(call, "Ошибка ID", show_alert=True)
            return

        parts = call.data.split("_")
        if len(parts) < 3: return

        toggle_type = parts[1]
        callback_user_id_encoded = parts[2]

        if sender_encoded_id != callback_user_id_encoded:
            utils.safe_answer_callback(call, "Вы не можете изменять чужие настройки.", show_alert=True)
            return

        settings = db.get_user_settings(sender_encoded_id)
        setting_key_map = {
            "blacklist": "blacklist_enabled",
            "reset": "reset_recipient",
            "answers": "answers"
        }
        setting_key = setting_key_map.get(toggle_type)

        if not setting_key:
            utils.safe_answer_callback(call, "Неизвестная настройка.")
            return

        new_value = not settings[setting_key]
        db.set_user_setting(sender_encoded_id, setting_key, new_value)
        settings[setting_key] = new_value

        ack_text_map = {
            "blacklist_enabled": lambda v: f"Кнопка блокировки: {'✅ Вкл' if v else '❌ Выкл'}",
            "reset_recipient": lambda v: f"Сброс получателя: {'✅ Да' if v else '❌ Нет'}",
            "answers": lambda v: f"Ответы на анонимки: {'✅ Вкл' if v else '❌ Выкл'}",
        }
        ack_text = ack_text_map[setting_key](new_value)

        utils.safe_answer_callback(call, ack_text)
        keyboard = ui.create_settings_keyboard(settings, sender_encoded_id)
        utils.safe_edit_markup(call.message.chat.id, call.message.message_id, reply_markup=keyboard)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("blacklist_"))
    def handle_blacklist_pagination(call: types.CallbackQuery):
        sender_encoded_id, _ = db.update_user_data(call.from_user)
        if not sender_encoded_id:
             utils.safe_answer_callback(call, "Ошибка ID")
             return

        parts = call.data.split("_")
        action = parts[1] # "prev" or "next"

        try:
            current_page = int(parts[2])
        except (IndexError, ValueError):
            utils.safe_answer_callback(call, "Ошибка пагинации")
            return

        new_page = current_page - 1 if action == "prev" else current_page + 1

        ui.send_blacklist_page(call.message.chat.id, call.message.message_id, sender_encoded_id, new_page, is_edit=True)
        utils.safe_answer_callback(call)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("unblock_"))
    def handle_unblock(call: types.CallbackQuery):
        blocker_encoded_id, _ = db.update_user_data(call.from_user)
        if not blocker_encoded_id:
            utils.safe_answer_callback(call, "Ошибка ID")
            return

        parts = call.data.split("_")
        if len(parts) < 3:
             utils.safe_answer_callback(call, "Ошибка данных кнопки")
             return

        target_id_two_encoded = parts[1]
        try:
            page_to_refresh = int(parts[2])
        except (IndexError, ValueError):
            page_to_refresh = 0

        db.remove_from_blacklist(blocker_encoded_id, target_id_two_encoded)
        utils.safe_answer_callback(call, "Пользователь разблокирован.")

        ui.send_blacklist_page(call.message.chat.id, call.message.message_id, blocker_encoded_id, page_to_refresh, is_edit=True)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("block_"))
    def handle_block(call: types.CallbackQuery):
        blocker_encoded_id, blocker_two_encoded_id = db.update_user_data(call.from_user)
        if not blocker_encoded_id:
            utils.safe_answer_callback(call, "Ошибка ID")
            return

        try:
            target_to_block_two_encoded = call.data.split("_")[1]
        except IndexError:
            utils.safe_answer_callback(call, "Ошибка данных кнопки")
            return

        if not db.is_user_blocked(blocker_encoded_id, target_to_block_two_encoded):
            db.add_to_blacklist(blocker_encoded_id, target_to_block_two_encoded)
            utils.safe_answer_callback(call, "Пользователь заблокирован.")
            utils.safe_edit_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        else:
            utils.safe_answer_callback(call, "Пользователь уже заблокирован.")
            utils.safe_edit_markup(call.message.chat.id, call.message.message_id, reply_markup=None)


    # --- Main Message Processing Handler (Handles all content types) ---
    @bot.message_handler(content_types=['text', 'photo', 'video', 'audio', 'document', 'voice', 'video_note', 'sticker', 'location', 'contact'])
    def process_message(message: types.Message):
        if message.text and message.text.startswith('/'):
             return
        sender = message.from_user
        sender_encoded_id, sender_two_encoded_id = db.update_user_data(sender)
        if not sender_encoded_id or not sender_two_encoded_id:
            utils.safe_reply(message, "Не удалось обработать ваш ID. Попробуйте /start")
            return

        sender_settings = db.get_user_settings(sender_encoded_id)
        target_encoded_id = None
        is_reply = False
        message_prefix = "Вам анонимка 🤫"

        # --- Determine the recipient ---
        if message.reply_to_message and message.reply_to_message.from_user.is_bot:
            original_sender_of_replied_msg = db.get_reply_sender(sender_encoded_id, message.reply_to_message.id)
            if original_sender_of_replied_msg:
                target_encoded_id = original_sender_of_replied_msg
                is_reply = True
                message_prefix = "Вам ответили на анонимку 💬"
            else:
                target_encoded_id = db.get_user_target(sender_encoded_id)
                if not target_encoded_id:
                    utils.safe_reply(message, "Не могу определить получателя для ответа на это сообщение. Попробуйте снова установить цель через ссылку /start.")
                    return
        else:
            target_encoded_id = db.get_user_target(sender_encoded_id)

        # --- Check if a target is determined ---
        if not target_encoded_id:
            utils.safe_reply(message,
                            f"Получатель не задан 🤷‍♀️\nИспользуйте ссылку вида <code>https://t.me/{BOT_NAME}?start=КОД_ПОЛУЧАТЕЛЯ</code> "
                            f"или ответьте на анонимное сообщение, чтобы отправить ответ.")
            return

        # --- Validate target ID and get target info ---
        target_decoded_id = utils.decode_user_id_to_int(target_encoded_id)
        if target_decoded_id is None:
            utils.safe_reply(message, "Ошибка: Неверный ID получателя. Возможно, ссылка устарела или повреждена. Цель сброшена.")
            db.set_user_target(sender_encoded_id, None)
            return

        target_settings = db.get_user_settings(target_encoded_id)

        # --- Check permissions and blocks ---
        if is_reply and not target_settings["answers"]:
            utils.safe_reply(message, "❌ Этот пользователь запретил ответы на свои анонимки.")
            return
        
        if db.is_user_blocked(target_encoded_id, sender_two_encoded_id):
            db.update_blacklist_last_message(target_encoded_id, sender_two_encoded_id)
            reply_text = "✅ Ответ успешно отправлен!" if is_reply else "✅ Анонимка успешно отправлена!"
            utils.safe_reply(message, reply_text)
            if not is_reply and sender_settings["reset_recipient"]:
                db.set_user_target(sender_encoded_id, None)
            db.increment_message_count(sender_encoded_id, sent=True)
            return

        # --- Prepare and send the message ---
        markup = types.InlineKeyboardMarkup()
        if target_settings["blacklist_enabled"]:
            block_button_text = "🚫 Заблокировать отвечателя" if is_reply else "🚫 Заблокировать отправителя"
            markup.add(types.InlineKeyboardButton(block_button_text, callback_data=f"block_{sender_two_encoded_id}"))

        success, error_msg = ui.send_anonymous_message(
            target_decoded_id, message, markup, message_prefix, sender_encoded_id, target_encoded_id
        )

        # --- Handle send result ---
        if success:
            reply_text = "✅ Ответ успешно отправлен!" if is_reply else "✅ Анонимка успешно отправлена!"
            utils.safe_reply(message, reply_text)
            if not is_reply and sender_settings["reset_recipient"]:
                 db.set_user_target(sender_encoded_id, None)
            db.increment_message_count(sender_encoded_id, sent=True)
            db.increment_message_count(target_encoded_id, sent=False)
        else:
             utils.safe_reply(message, f"⚠️ {error_msg}" or "⚠️ Произошла ошибка при отправке.")

    print("Handlers registered.")