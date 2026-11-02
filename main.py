import telebot, hashlib, json, random
from telebot import types
from datetime import datetime, timedelta

MAIN_TOKEN = "token_1"
TEST_TOKEN = "token_1"

TEST_BOT_NAME = "test_bot"

testing = False
if testing:
    TOKEN = TEST_TOKEN
else:
    TOKEN = MAIN_TOKEN

bot = telebot.TeleBot(TOKEN)

cards = {
    "обычная": {"points": 10,
                "chance": 70,
                "склонение_1": "Обычная"},
    "редкая": { "points": 50,
                "chance": 20, ""
                "склонение_1": "Редкая"},
    "мифическая": {"points": 200,
                   "chance": 8,
                   "склонение_1": "Мифическая"},
    "легендарная": {"points": 500,
                    "chance": 2,
                    "склонение_1":"Легендарная"}
}

def load_json(filename):
    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_json(data, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

chats_settings = load_json("chats_settings.json")
photo_id_mapping = load_json("photo_id_mapping.json")
users_data = load_json("users_data.json")
user_cooldowns = load_json("user_cooldowns.json")

def get_user_data(chat_id, user_id):
    chat_data = chats_settings.get(str(chat_id), {})
    user_data = chat_data.get("users", {}).get(str(user_id), {"points": 0, "cards": []})
    return user_data

def update_user_data(chat_id, user_id, updated_data):
    chat_data = chats_settings.get(str(chat_id), {})
    chat_data.setdefault("users", {})[str(user_id)] = updated_data
    update_and_save(chats_settings, str(chat_id), chat_data, "chats_settings.json")

def generate_short_id(photo_id):
    return hashlib.md5(photo_id.encode()).hexdigest()[:10]

def update_and_save(target_dict, key, value, file):
    target_dict[key] = value
    with open(file, "w", encoding="utf-8") as f:
        json.dump(target_dict, f, ensure_ascii=False, indent=4)

def choose_card():
    rarities = list(cards.keys())
    chances = [cards[rarity]["chance"] for rarity in rarities]
    chosen_rarity = random.choices(rarities, weights=chances, k=1)[0]
    return cards[chosen_rarity], chosen_rarity

def is_admin(chat_id, user_id):
    chat_admins = chats_settings[str(chat_id)]['admins']
    return int(user_id) in chat_admins

def get_cooldown_time(chat_id):
    chat_settings = chats_settings.get(str(chat_id), {})
    cooldown_settings = chat_settings.get("cooldown", {})
    hours = cooldown_settings.get("hours", 0)
    minutes = cooldown_settings.get("minutes", 0)
    seconds = cooldown_settings.get("seconds", 60)
    total_seconds = hours * 3600 + minutes * 60 + seconds
    return total_seconds

def handle_admin_start(message, chat_id, edit=False):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("Карточки", callback_data=f"cards_{chat_id}"),
        types.InlineKeyboardButton("Администраторы", callback_data=f"admins_{chat_id}"),
        types.InlineKeyboardButton("Задержка", callback_data=f"cooldown_{chat_id}"),
        types.InlineKeyboardButton("Триггерное слово", callback_data=f"trigger_word_{chat_id}")
    )
    if edit:
        bot.edit_message_text(f"Панель управления чатом {chats_settings[chat_id]['name']}", message.chat.id, message.id, reply_markup=markup)
    else:
        bot.reply_to(message, f"Панель управления чатом {chats_settings[chat_id]['name']}", reply_markup=markup)

def handle_admin_cards(call, chat_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("Добавить карточку", callback_data=f"add_card_{chat_id}"),
        types.InlineKeyboardButton("Удалить карточку", callback_data=f"remove_card_{chat_id}")
    )
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"Управление карточками для чата {chat_id}",
        reply_markup=markup
    )

def handle_admin_admins(call, chat_id):
    chat_name = chats_settings[chat_id]['name']
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("Добавить администратора", callback_data=f"add_admin_{chat_id}"),
        types.InlineKeyboardButton("Удалить администратора", callback_data=f"remove_admin_{chat_id}")
    )
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"Управление администраторами для {chat_name}",
        reply_markup=markup
    )

def handle_admin_cooldown(call, chat_id):
    msg = bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"Установите задержку в формате `ЧЧ:MM:СС` (часы, минуты, секунды):"
    )
    bot.register_next_step_handler(msg, process_cooldown_setting, chat_id)

@bot.message_handler(commands=['start'])
def settings_handler(message):
    if message.chat.type == "private":
        if len(message.text.split()) > 1:
            start_target = message.text.split()[1]
            if str(start_target[0:9]) == "settings_":
                chat_id = message.text.split("_")[1]
                if not is_admin(chat_id, message.from_user.id):
                    bot.send_message(message.chat.id, f"Вы не являетесь администратором чата.")
                    return
                handle_admin_start(message, chat_id)

        else:
            bot_username = bot.get_me().username
            invite_link = f"https://t.me/{bot_username}?startgroup=true"
            markup = types.InlineKeyboardMarkup()
            invite_button = types.InlineKeyboardButton("Добавить бота в группу", url=invite_link)
            markup.add(invite_button)
            bot.reply_to(message, "Чтобы добавить меня в группу, нажмите кнопку ниже:", reply_markup=markup)


@bot.message_handler(content_types=['new_chat_members'])
def new_member_greeting(message):
    if message.new_chat_members[0].id == bot.get_me().id:
        bot.send_message(message.chat.id, "Привет! Я бот для карточек.\nДорогой админ, прошу тебя, настрой меня..")
        chat_id = message.chat.id

        admins = bot.get_chat_administrators(chat_id)
        admin_names = []
        for admin in admins:
            user_id = str(admin.user.id)
            admin_names.append(admin.user.id)
            user_data = users_data.get(user_id, {})
            if not chat_id in user_data.get('admin_in_chats', []):
                user_data.setdefault('admin_in_chats', []).append(chat_id)
                update_and_save(users_data, user_id, user_data, "users_data.json")
        if not str(chat_id) in chats_settings.keys():
            new_chat = {
                "name": message.chat.title,
                "cards": {
                    "обычная": [],
                    "редкая": [],
                    "мифическая": [],
                    "легендарная": []
                },
                "users": {},
                "admins": admin_names
            }
            chats_settings[str(chat_id)] = new_chat
            update_and_save(chats_settings, str(chat_id), new_chat, "chats_settings.json")


@bot.message_handler(commands=['settings'])
def settings_handler(message):
    if message.chat.type == "private":
        if len(message.text.split()) > 1 and message.text.split()[1].startswith("settings_"):
          chat_id = message.text.split("_")[1]
          user_id = message.from_user.id
          if is_admin(chat_id, message.from_user.id):
              handle_admin_start(message, chat_id)
          else:
              bot.send_message(message.chat.id, f"Вы не являетесь администратором чата.")
        else:
            markup = types.InlineKeyboardMarkup()
            user_id = message.from_user.id
            admin_in_chats = users_data.get(str(user_id), {}).get("admin_in_chats", [])
            for chat_id in admin_in_chats:
                chat_id = str(chat_id)
                if chat_id in chats_settings.keys():
                    button = types.InlineKeyboardButton(chats_settings[chat_id]["name"], callback_data=f"settings_{chat_id}")
                    markup.add(button)
            bot.reply_to(message, "Выберите чат для настройки", reply_markup=markup)
    else:
        if is_admin(message.chat.id, message.from_user.id):
            markup = types.InlineKeyboardMarkup()
            button = types.InlineKeyboardButton("Настроить", url=f"https://t.me/{bot.get_me().username}?start=settings_{message.chat.id}")
            markup.add(button)
            bot.reply_to(message, "Перейдите в личные сообщения для настройки", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("settings_"))
def chat_settings_callback(call):
    chat_id = call.data.split("_")[1]
    if is_admin(chat_id, call.message.chat.id):
        handle_admin_start(call.message, chat_id, True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("cards_"))
def cards_callback(call):
    chat_id = call.data.split("_")[1]
    handle_admin_cards(call, chat_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("admins_"))
def admins_callback(call):
    chat_id = call.data.split("_")[1]
    handle_admin_admins(call, chat_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("cooldown_"))
def cooldown_callback(call):
    chat_id = call.data.split("_")[1]
    handle_admin_cooldown(call, chat_id)

def process_cooldown_setting(message, chat_id):
    try:
        time_str = message.text.strip()
        hours, minutes, seconds = map(int, time_str.split(':'))
        if any(x < 0 for x in [hours, minutes, seconds]):
            raise ValueError("Time values cannot be negative.")


        chats_settings.setdefault(chat_id, {}).setdefault("cooldown", {})["hours"] = hours
        chats_settings[chat_id]["cooldown"]["minutes"] = minutes
        chats_settings[chat_id]["cooldown"]["seconds"] = seconds

        update_and_save(chats_settings, chat_id, chats_settings[chat_id], "chats_settings.json")

        bot.reply_to(message, f"Задержка установлена на {hours} часов, {minutes} минут, {seconds} секунд.")

    except ValueError:
        bot.reply_to(message, "Неверный формат времени. Используйте `ЧЧ:MM:СС`.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("add_card_"))
def add_card_callback(call):
    chat_id = call.data.split("_")[2]
    markup = types.InlineKeyboardMarkup()
    for rarity in cards.keys():
        callback_data = f"rarity_selected_{chat_id}_{rarity}"
        markup.add(types.InlineKeyboardButton(rarity.capitalize(), callback_data=callback_data))
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text="Выберите редкость для новой карточки:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("rarity_selected_"))
def process_card_photo(call):
    chat_id, rarity = call.data.split("_")[2:]
    msg = bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                text=f"Теперь отправьте фото для карточки:")
    bot.register_next_step_handler(msg, process_card_name, chat_id, rarity)

def process_card_name(message, chat_id, rarity):
    if message.content_type == 'photo':
        photo_id = message.photo[-1].file_id
        short_id = generate_short_id(photo_id)
        photo_id_mapping[short_id] = photo_id
        update_and_save(photo_id_mapping, short_id, photo_id, "photo_id_mapping.json")

        if message.caption:
            card_name = message.caption.strip().replace(" ", "_")
            save_card_data(chat_id, rarity, short_id, card_name)
            bot.reply_to(message, f"Карточка \"{card_name.replace('_', ' ')}\" добавлена.")
            return

        msg = bot.reply_to(message, "Введите название для карточки:")
        bot.register_next_step_handler(msg, process_card_final_name, chat_id, rarity, short_id)

    else:
        msg = bot.reply_to(message, "Пожалуйста, отправьте фото карточки.")
        bot.register_next_step_handler(msg, process_card_name, chat_id, rarity)

def process_card_final_name(message, chat_id, rarity, short_id):
    if message.caption:
     card_name = message.caption.strip().replace(" ", "_")
     save_card_data(chat_id, rarity, short_id, card_name)
     bot.reply_to(message, f"Карточка \"{card_name.replace('_', '' '')}\" добавлена.")

def save_card_data(chat_id, rarity, short_id, card_name):
    if chat_id not in chats_settings:
        chats_settings[chat_id] = {"name": f"Chat {chat_id}", "cards": {}}
    if rarity not in chats_settings[chat_id]["cards"]:
        chats_settings[chat_id]["cards"][rarity] = []

    new_card = {short_id: {"name": card_name.replace("_", " "), "photo_id": short_id}}
    chats_settings[chat_id]["cards"][rarity].append(new_card)
    update_and_save(chats_settings, chat_id, chats_settings[chat_id], "chats_settings.json")


@bot.callback_query_handler(func=lambda call: call.data.startswith("remove_card_"))
def remove_card_callback(call):
    chat_id = call.data.split("_")[2]
    chat_settings = chats_settings.get(chat_id, {})

    if not chat_settings or not chat_settings.get("cards"):
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text="В этом чате нет карточек.")
        return

    markup = types.InlineKeyboardMarkup()
    for rarity in cards.keys():
        callback_data = f"remove_rcard_rarity_{chat_id}_{rarity}"
        markup.add(types.InlineKeyboardButton(rarity.capitalize(), callback_data=callback_data))
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text="Выберите редкость карточки для удаления:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("remove_rcard_rarity_"))
def remove_card_rarity_callback(call):
    chat_id, rarity = call.data.split("_")[3:]
    chat_settings = chats_settings.get(chat_id, {})
    print(1)

    if not chat_settings or not chat_settings.get("cards") or not chat_settings["cards"].get(rarity):
        bot.answer_callback_query(call.id, "В этом чате нет карточек данной редкости.")
        return

    cards_of_rarity = chat_settings["cards"][rarity]

    if not cards_of_rarity:
        bot.answer_callback_query(call.id, "Карточки данной редкости не найдены.")
        return

    total_pages = (len(cards_of_rarity) + 9) // 10
    display_card_page(call.message.chat.id, chat_id, cards_of_rarity, page=1, total_pages=total_pages, rarity=rarity)

def display_card_page(chat_id, chat_id_str, cards, page, total_pages, rarity):
    start_index = (page - 1) * 10
    end_index = start_index + 10
    cards_page = cards[start_index:end_index]

    media = []
    if cards_page:
        for i, card in enumerate(cards_page, start=start_index + 1):
            for card_id, card_info in card.items():
                media.append(telebot.types.InputMediaPhoto(photo_id_mapping[card_id]))

    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []

    if cards_page:
        for i, card in enumerate(cards_page, start=start_index + 1):
            for card_id, card_info in card.items():
                buttons.append(
                    types.InlineKeyboardButton(
                        f"{i}. {card_info['name']}",
                        callback_data=f"delete_card_{chat_id_str}_{card_id}_{rarity}"
                    )
                )

    for i in range(0, len(buttons), 2):
        markup.add(*buttons[i:i + 2])

    nav_buttons = []
    if page > 1:
        nav_buttons.append(
            types.InlineKeyboardButton("⬅️ Назад", callback_data=f"page_{chat_id_str}_{page - 1}_{rarity}"))
    if page < total_pages:
        nav_buttons.append(
            types.InlineKeyboardButton("Вперёд ➡️", callback_data=f"page_{chat_id_str}_{page + 1}_{rarity}"))

    if nav_buttons:
        markup.add(*nav_buttons)

    if media:
        bot.send_media_group(chat_id, media)

    bot.send_message(chat_id, f"Выберите карточку\nСтраница {page} из {total_pages}", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("page_"))
def handle_pagination(call):
    chat_id, page_str, rarity = call.data.split("_")[1:]
    page = int(page_str)

    chat_settings = chats_settings.get(chat_id, {})
    if not chat_settings or not chat_settings.get("cards") or not chat_settings["cards"].get(rarity):
        bot.answer_callback_query(call.id, "В этом чате нет карточек для отображения.")
        return

    cards = chat_settings["cards"][rarity]
    total_pages = (len(cards) + 9) // 10

    display_card_page(call.message.chat.id, chat_id, cards, page=page, total_pages=total_pages, rarity=rarity)

@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_card_"))
def delete_card_callback(call):
    chat_id, short_id, rarity = call.data.split("_")[2:]

    chat_settings = chats_settings.get(chat_id, {})

    if not chat_settings or not chat_settings.get("cards") or not chat_settings["cards"].get(rarity):
        bot.answer_callback_query(call.id, "Этой карточки уже нет.")
        return

    card_to_remove = None
    card_name = ""
    for card in chat_settings["cards"][rarity]:
        if short_id in card:
            card_name = card[short_id]['name']
            card_to_remove = card
            break
    if card_to_remove:
        chat_settings["cards"][rarity].remove(card_to_remove)
        update_and_save(chats_settings, chat_id, chat_settings, "chats_settings.json")
        bot.answer_callback_query(call.id, f"Карточка '{card_name}' была удалена.")
    else:
        bot.answer_callback_query(call.id, "Карточка не найдена для удаления.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("add_admin_"))
def add_admin_callback(call):
    chat_id = call.data.split("_")[2]
    if not is_admin(chat_id, call.from_user.id):
        bot.answer_callback_query(call.id, "Вы не администратор этого чата.")
        return

    msg = bot.send_message(call.message.chat.id, "Перешлите сообщение от пользователя, которого хотите сделать администратором:")
    bot.register_next_step_handler(msg, process_add_admin, chat_id)

def process_add_admin(message, chat_id):
    if message.forward_from:
        new_admin_id = message.forward_from.id
        if not is_admin(chat_id, new_admin_id): # Prevent duplicates
            chats_settings.get(chat_id, {}).get('admins', []).append(new_admin_id)
            users_data.get(str(new_admin_id), {}).get('admin_in_chats', []).append(int(chat_id))
            update_and_save(users_data, str(new_admin_id), users_data[str(new_admin_id)], "users_data.json")
            update_and_save(chats_settings, chat_id, chats_settings[chat_id], "chats_settings.json")
            bot.reply_to(message, f"Пользователь добавлен в администраторы.")
        else:
            bot.reply_to(message, f"Пользователь уже является администратором.")
    else:
        bot.reply_to(message, "Это не пересланное сообщение.\nЛибо пользователь запретил пересылать сообщения.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("remove_admin_"))
def remove_admin_callback(call):
    chat_id = call.data.split("_")[2]
    if not is_admin(chat_id, call.from_user.id):
        bot.answer_callback_query(call.id, "Вы не администратор этого чата.")
        return

    msg = bot.send_message(call.message.chat.id, "Перешлите сообщение от администратора, которого хотите удалить:")
    bot.register_next_step_handler(msg, process_remove_admin, chat_id)

def process_remove_admin(message, chat_id):
    if message.forward_from:
        admin_to_remove_id = message.forward_from.id
        if is_admin(chat_id, admin_to_remove_id):
            chats_settings[chat_id]['admins'].remove(admin_to_remove_id)
            if len(chats_settings[chat_id]['admins']) == 1:
                chats_settings[chat_id]['admins'].append(admin_to_remove_id)
                bot.reply_to(message, f"В списке администраторов должно быть не менее одного пользователя.")
                return
            users_data[str(admin_to_remove_id)]['admin_in_chats'].remove(int(chat_id))
            update_and_save(chats_settings, chat_id, chats_settings[chat_id], "chats_settings.json")
            update_and_save(users_data, str(admin_to_remove_id), users_data[str(admin_to_remove_id)], "users_data.json")
            bot.reply_to(message, f"Пользователь удален из администраторов.")
        else:
            bot.reply_to(message, f"Пользователь не является администратором.")


    else:
        bot.reply_to(message, "Это не пересланное сообщение.\nЛибо пользователь запретил пересылать сообщения.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("trigger_word_"))
def trigger_word_callback(call):
    chat_id = call.data.split("_")[2]
    msg = bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"Установите триггерное слово для чата {chat_id}:"
    )
    bot.register_next_step_handler(msg, process_trigger_word_setting, chat_id)


def process_trigger_word_setting(message, chat_id):
    trigger_word = message.text.strip()
    chats_settings[chat_id]["trigger_word"] = trigger_word
    save_json(chats_settings, "chats_settings.json")
    bot.reply_to(message, f"Триггерное слово установлено: {trigger_word}")


@bot.message_handler(func=lambda message: message.text.lower() == chats_settings.get(str(message.chat.id), {}).get("trigger_word", "карта"))
def handle_trigger_word(message):
    chat_id_str = str(message.chat.id)
    user_id_str = str(message.from_user.id)

    chat_data = chats_settings.get(chat_id_str)
    if not chat_data:
        bot.reply_to(message, "Этот чат не настроен для игры с карточками.")
        return

    trigger_word = chat_data.get("trigger_word", "карта")
    if trigger_word.lower() not in message.text.lower():
        return

    rarity_data, rarity = choose_card()

    cards = chat_data["cards"].get(rarity)
    if not cards:
        bot.reply_to(message,
                     f'Вы могли бы получить карточку с редкостью "{rarity}", но к сожалению админ не добавил...')
        return

    cooldown_duration = get_cooldown_time(chat_id_str)

    now = datetime.now()
    cooldown_end = user_cooldowns.get(user_id_str, {}).get(chat_id_str)

    if cooldown_end and now < datetime.strptime(cooldown_end, '%Y-%m-%d %H:%M:%S.%f'):
        remaining_time = datetime.strptime(cooldown_end, '%Y-%m-%d %H:%M:%S.%f') - now
        seconds = int(remaining_time.total_seconds())
        bot.reply_to(message, f"Подождите {seconds} секунд перед следующей попыткой.")
        return

    cd = {chat_id_str: str(now + timedelta(seconds=cooldown_duration))}

    user_cooldowns.get(user_id_str, {}).setdefault(chat_id_str, cd)
    update_and_save(user_cooldowns, user_id_str, cd, "user_cooldowns.json")

    user_data = get_user_data(chat_id_str, user_id_str)
    user_data['points'] += rarity_data['points']
    card = random.choice(cards)

    for card_data in card.values():
        short_id = card_data["photo_id"]
        card_name = card_data["name"]
    photo_id = photo_id_mapping.get(short_id)
    if not photo_id:
        bot.reply_to(message, "Ошибка: не найден ID фотографии для этой карты.")
        return

    print(photo_id)
    user_cards = user_data.get('cards', [])
    card_u_user = short_id in user_cards
    if not card_u_user:
        user_cards.append(short_id)

        caption = f"""🃏 Карточка «<b>{card_name}</b>» добавлена.

💎 Редкость • <b>{rarity_data['склонение_1']}</b>
✨ Очки • +<b>{rarity_data['points']}</b> [<b>{user_data['points']}</b>]
    """
    else:
        caption = f"""🃏 Выпала карта «<b>{card_name}</b>», но она у вас уже есть.

💎 Редкость • <b>{rarity_data['склонение_1']}</b>
✨ Очки • +<b>{rarity_data['points']}</b> [<b>{user_data['points']}</b>]
            """

    bot.send_photo(
        message.chat.id,
        photo_id,
        caption=str(caption),
        parse_mode="html"
    )

    update_user_data(chat_id_str, user_id_str, user_data)

if __name__ == "__main__":
    print("Бот запущен.")
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            print(e)
