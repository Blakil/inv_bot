import logging
import time
import threading
import json
import re
from pyrogram import Client, filters, enums
from pyrogram.types import Message, ChatMemberUpdated, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from pyrogram.raw import functions, types
from pyrogram.handlers import MessageHandler
import psycopg2
import os
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

# Мьютекс для контроля доступа к файлу
file_lock = threading.Lock()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота
app = Client("referral_bot", api_id=int(os.getenv("API_ID")), api_hash=os.getenv("API_HASH"), bot_token=os.getenv("BOT_TOKEN"))

# Подключение к базе данных
conn = psycopg2.connect(
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASS"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT")
)
cursor = conn.cursor()

# Создание мьютекса для синхронизации доступа к базе данных
#db_lock = threading.Lock()

# Состояния
START_STATE = "start"
MAIN_MENU_STATE = "main_menu"
USER_GIVEAWAY_LINK = "user_giveaway_link"
ADMIN_PANEL_STATE = "admin_panel"
CREATE_GIVEAWAY_LINK = "create_giveaway_link"
SET_DURATION_STATE = "set_duration"
INPUT_DURATION_STATE = "input_duration"
GIVEAWAY_NAME_SET = "giveaway_name_set"
SET_PRIZES_STATE = "set_prizes"
POST_GIVEAWAY_STATE = "post_giveaway"
REFERRAL_LINKS_STATE = "referral_links"
LEADERBOARD_STATE = "leaderboard"
MY_REFERRALS_STATE = "my_referrals"
ABOUT_BOT_STATE = "about_bot"
ABOUT_BOT_STATE_ADMIN = "about_bot_admin"
ADMIN_GIVEAWAYS_STATE = "admin_giveaways"

def get_channels_from_db():
    try:
        cursor.execute("SELECT chat_id, title, username FROM chats WHERE accessible = TRUE")
        channels = [{'chat_id': row[0], 'name': row[1], 'username': row[2]} for row in cursor.fetchall()]
        return channels
    except Exception as e:
        print(f"Ошибка при подключении к базе данных: {e}")
        return []
    
def get_giveaways_from_db():
    giveaways = []
    try:
        cursor.execute("""
            SELECT id, user_id, chat_id, name, duration_type, duration, prizes, created_at
            FROM giveaways
            ORDER BY created_at DESC
        """)
        rows = cursor.fetchall()
        for row in rows:
            giveaway = {
                'id': row[0],
                'user_id': row[1],
                'chat_id': row[2],
                'name': row[3],
                'duration_type': row[4],
                'duration': row[5],
                'prizes': row[6],
                'created_at': row[7]
            }
            giveaways.append(giveaway)
    except Exception as e:
        logger.error(f"Ошибка при получении списка розыгрышей: {e}")
        return []
    return giveaways

data_file = 'user_data.json'

def GET_STATE(user_id):
    """ Возвращает состояние пользователя по его user_id. """
    # Попытка извлечь user_state для данного user_id
    # Если user_id отсутствует в user_data, вернуть пустую строку как состояние по умолчанию
    user_data = load_user_data(user_id)
    logger.info(str(user_data.get('user_state', '')))
    return user_data.get('user_state', '')

def GET_PROPERTY(user_id, property):
    """ Возвращает состояние пользователя по его user_id. """
    # Попытка извлечь user_state для данного user_id
    # Если user_id отсутствует в user_data, вернуть пустую строку как состояние по умолчанию
    user_data = load_user_data(user_id)
    return user_data.get(property, '')

def SET_STATE(user_id, new_state):
    """ Устанавливает новое состояние для пользователя по его user_id. """
    user_data = load_user_data(user_id)  # Загружаем текущие данные пользователя
    user_data['user_state'] = new_state  # Устанавливаем новое состояние
    save_user_data(user_id, user_data)  # Сохраняем обновленные данные

def SET_PROPERTY(user_id, property, value):
    """ Устанавливает новое состояние для пользователя по его user_id. """
    user_data = load_user_data(user_id)  # Загружаем текущие данные пользователя
    user_data[property] = value  # Устанавливаем новое состояние
    save_user_data(user_id, user_data)  # Сохраняем обновленные данные

def clean_text(text):
    """ Очистка текста от потенциально опасных символов. """
    # Удаление SQL спецсимволов
    text = re.sub(r'[;\'"\\]', '', text)
    # Опционально, удаление HTML тегов или других опасных паттернов
    text = re.sub(r'<[^>]*>', '', text)
    return text.strip()

def save_user_data(user_id, user_data):
    """ Сохраняем данные пользователя в файл """
    with file_lock:  # Блокировка для предотвращения одновременного доступа
        # Загрузка существующих данных
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                all_data = json.load(f)
        except FileNotFoundError:
            all_data = {}

        # Обновление данных для данного user_id
        all_data[str(user_id)] = user_data

        # Сохранение обновленных данных обратно в файл
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=4)

def load_user_data(user_id):
    """ Загружаем данные пользователя из файла """
    with file_lock:
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                all_data = json.load(f)
            return all_data.get(str(user_id), {})
        except FileNotFoundError:
            return {}

def load_all_data():
    """ Загружаем все данные при старте программы """
    with file_lock:
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        


def ADMIN_STATE(key):
    return (key == ADMIN_PANEL_STATE or key == CREATE_GIVEAWAY_LINK or key == SET_DURATION_STATE or key == SET_PRIZES_STATE or key == POST_GIVEAWAY_STATE or key == ABOUT_BOT_STATE_ADMIN or key == ADMIN_GIVEAWAYS_STATE or key == INPUT_DURATION_STATE or key == GIVEAWAY_NAME_SET)

def USER_STATE(key):
    return (key == START_STATE or key == MAIN_MENU_STATE or key == REFERRAL_LINKS_STATE or key == LEADERBOARD_STATE or key == MY_REFERRALS_STATE or key == ABOUT_BOT_STATE or key == USER_GIVEAWAY_LINK)

def create_giveaway_buttons():
    buttons = [
        [KeyboardButton("Создать розыгрыш")],
        [KeyboardButton("Назад")]
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# Кнопки

CHANNELS_PER_PAGE = 8

user_selection_active = {}
user_selection_output = {}

def create_universal_keyboard(user_id, items, page, items_destination, item_name_key):
    user_selection_active[user_id] = {}
    user_selection_active[user_id]["items"] = items
    user_selection_active[user_id]["items_destination"] = items_destination
    user_selection_active[user_id]["item_name_key"] = item_name_key
    max_pages = len(items) // CHANNELS_PER_PAGE + (1 if len(items) % CHANNELS_PER_PAGE else 0)
    page = max(1, min(page, max_pages))
    start = (page - 1) * CHANNELS_PER_PAGE
    end = min(start + CHANNELS_PER_PAGE, len(items))
    buttons = [
        [InlineKeyboardButton(item[item_name_key], callback_data=f"{items_destination}_{start + index}")]
        for index, item in enumerate(items[start:end])
    ]
    navigation_buttons = []
    if page > 1:
        navigation_buttons.append(InlineKeyboardButton("⬅️ Назад", f"page_{page - 1}"))
    if page < max_pages:
        navigation_buttons.append(InlineKeyboardButton("Вперёд ➡️", callback_data=f"page_{page + 1}"))
    if navigation_buttons:
        buttons.append(navigation_buttons)
    return InlineKeyboardMarkup(buttons)

# Пример использования функции в обработчике callback
@app.on_callback_query()
def handle_callback_query(client, callback_query):
    user_id = callback_query.from_user.id
    data = user_selection_active[user_id]["items"]
    items_destination = user_selection_active[user_id]["items_destination"]
    item_name_key = user_selection_active[user_id]["item_name_key"]
    STRING_KEY = callback_query.data
    

    # Обработка активности пользователя
    if not user_selection_active.get(user_id, False):
        callback_query.message.edit_text("...")
        return

    # Предполагаем, что items уже загружены и переданы в контексте
    if STRING_KEY.startswith(items_destination):
        index = int(STRING_KEY.split("_")[1])
        item = data[index] 
        SET_PROPERTY(user_id, items_destination, index)
        text = f"Вы выбрали: {item[item_name_key]}"
        callback_query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Продолжить", callback_data="continue")],
                [InlineKeyboardButton("Назад к списку", callback_data="back_to_list")]
            ])
        )
    elif STRING_KEY.startswith("page_"):
        page = int(STRING_KEY.split("_")[1])
        markup = create_universal_keyboard(data, page, items_destination, item_name_key)
        callback_query.message.edit_text("Выберите:", reply_markup=markup)
    elif STRING_KEY == "continue":
        selected_index = GET_PROPERTY(user_id, items_destination)
        selected_item = data[selected_index]
        user_selection_output = user_selection_active
        user_selection_active[user_id] = False
        callback_query.message.reply(f"Выбрано: {selected_item[item_name_key]}", reply_markup=continue_button())

# Функция для создания клавиатуры с каналами
def create_channel_keyboard(page):
    chann = get_channels_from_db()
    max_pages = len(chann) // CHANNELS_PER_PAGE + (1 if len(chann) % CHANNELS_PER_PAGE else 0)
    page = max(1, min(page, max_pages))
    start = (page - 1) * CHANNELS_PER_PAGE
    end = min(start + CHANNELS_PER_PAGE, len(chann))
    buttons = [
        [InlineKeyboardButton(ch["name"], callback_data=f"channel_{index}")]
        for index, ch in enumerate(chann[start:end], start=start)
    ]
    navigation_buttons = []
    if page > 1:
        navigation_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"page_{page - 1}"))
    if page < max_pages:
        navigation_buttons.append(InlineKeyboardButton("Вперёд ➡️", callback_data=f"page_{page + 1}"))
    if navigation_buttons:
        buttons.append(navigation_buttons)
    return InlineKeyboardMarkup(buttons)

# Хэндлер для обработки callback queries от кнопок каналов и навигации
@app.on_callback_query()
def handle_callback_query(client, callback_query):
    user_id = callback_query.from_user.id
    if not user_selection_active.get(user_id, False):
        callback_query.message.edit_text("...")
        return

    data = callback_query.data
    if data.startswith("channel_"):
        index = int(data.split("_")[1])
        channels = get_channels_from_db()
        channel = channels[index]
        #user_data[user_id]["selected_channel"] = index  # Сохранение выбранного канала
        SET_PROPERTY(user_id, "selected_channel", index)
        if channel['username'] != "":
            # Если у канала есть username, создаем ссылку на канал
            channelll_link = f"https://t.me/{channel['username']}"
            text = f"Вы выбрали канал: [{channel['name']}]({channelll_link})"
        else:
            # Если username отсутствует, выводим просто название канала
            text = f"Вы выбрали канал: {channel['name']}"
        callback_query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Продолжить", callback_data="continue")],
                [InlineKeyboardButton("Назад к списку", callback_data="back_to_list")]
            ])
        )
    elif data.startswith("page_"):
        page = int(data.split("_")[1])
        callback_query.message.edit_text("Выберите канал:", reply_markup=create_channel_keyboard(page))
    elif data == "back_to_list":
        callback_query.message.edit_text("Выберите канал:", reply_markup=create_channel_keyboard(1))
    elif data == "continue":
        #selected_index = user_data[user_id]["selected_channel"]
        selected_index = GET_PROPERTY(user_id, "selected_channel")
        channels = get_channels_from_db()
        selected_channel = channels[selected_index]
        SET_PROPERTY(user_id, "giveaway_channel_id", selected_channel['chat_id'])
        #callback_query.message.edit_text(f"Выбран канал: {selected_channel['name']}", reply_markup=continue_button())
        callback_query.message.reply(f"Выбран канал: {selected_channel['name']}", reply_markup=continue_button())
        user_selection_active[user_id] = False  # Завершение процесса выбора

def main_menu_buttons():
    buttons = [
        [KeyboardButton("Реферальные ссылки"), KeyboardButton("Лидерборд")],
        [KeyboardButton("Мои рефералы"), KeyboardButton("О боте")]
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def admin_panel_buttons():
    buttons = [
        [KeyboardButton("Розыгрыши")],
        [KeyboardButton("О боте")],
        [KeyboardButton("Выйти с режима администратора")]
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def back_button():
    return ReplyKeyboardMarkup([[KeyboardButton("Назад")]], resize_keyboard=True)

def continue_button():
    return ReplyKeyboardMarkup([[KeyboardButton("Назад"), KeyboardButton("Продолжить")]], resize_keyboard=True)

def start_button():
    return ReplyKeyboardMarkup([[KeyboardButton("Начать")]], resize_keyboard=True)

def duration_buttons():
    return ReplyKeyboardMarkup([[KeyboardButton("Часы")], [KeyboardButton("Дни")], [KeyboardButton("Назад")]], resize_keyboard=True)

def about_bot_buttons():
    return ReplyKeyboardMarkup([[KeyboardButton("Назад"), KeyboardButton("Перейти в админскую панель")]], resize_keyboard=True)
def about_bot_admin_buttons():
    return ReplyKeyboardMarkup([[KeyboardButton("Назад"), KeyboardButton("Выйти с режима админа")]], resize_keyboard=True)

# Переменная для хранения состояний пользователей и промежуточных данных
#user_states = {}
#user_data = {}

def DB_create_giveaway(user_id, chat_id, name, duration_type, duration, prizes):
    try:
        # Проверка, существует ли уже розыгрыш для данного chat_id
        cursor.execute("""
            SELECT id FROM giveaways
            WHERE chat_id = %s
        """, (chat_id,))
        existing = cursor.fetchone()

        if existing:
            logger.info(f"Розыгрыш для канала с chat_id {chat_id} уже существует с ID {existing[0]}.")
            return False, existing[0]  # Возвращаем False, если розыгрыш уже существует

        # Вставка новых данных о розыгрыше, если такого нет
        cursor.execute("""
            INSERT INTO giveaways (user_id, chat_id, name, duration_type, duration, prizes, created_at, completed)
            VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, FALSE)
            RETURNING id
        """, (user_id, chat_id, name, duration_type, duration, prizes))
        giveaway_id = cursor.fetchone()[0]
        
        # Логирование успешного создания розыгрыша
        logger.info(f"Розыгрыш '{name}' успешно создан с ID {giveaway_id}.")
        
        # Подтверждение транзакции
        conn.commit()
        return True, giveaway_id  # Возвращаем True, указывая на успешное создание
    except Exception as e:
        # Логирование ошибки и откат изменений
        logger.error(f"Ошибка при создании розыгрыша: {e}")
        conn.rollback()
        return False, -500



def DB_add_chat(channel_id, channel_name, channel_username, accessible):

    try:
        cursor.execute("""
            INSERT INTO chats (chat_id, title, username, accessible)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (chat_id) DO UPDATE SET
            title = EXCLUDED.title,
            username = EXCLUDED.username,
            accessible = EXCLUDED.accessible
        """, (channel_id, channel_name, channel_username, accessible))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()  # Откат транзакции в случае ошибки
        return False
    finally:
        return True

@app.on_chat_member_updated()
def track_new_members(client, update: ChatMemberUpdated):
    try:
        if update.new_chat_member.user.is_bot and update.new_chat_member.user.id == app.get_me().id:
            logger.info(f"{update.chat}")
            channel_id = update.chat.id
            channel_name = update.chat.title
            channel_username = ""
            logger.info(f"{channel_id}")
            try:
                chat = client.get_chat(channel_id)
                try:
                    channel_username = update.chat.channel_username
                except Exception as eee:
                    channel_username = ""
                DB_add_chat(channel_id, channel_name, channel_username, True)
                print(f"Бот добавлен на канал {channel_name}")
            except Exception as e:
                if '406' in str(e):
                    print(f"У бота нет доступа к группе/каналу {channel_name}, ошибка 406 CHANNEL_PRIVATE")
                    DB_add_chat(channel_id, channel_name, channel_username, False)
                else:
                    print(f"Ошибка: {e}")

            logger.info(f"id: {channel_id}, name:{channel_name}")
        if update.new_chat_member and update.new_chat_member.user:
            referred_id = update.new_chat_member.user.id
            logger.info(f"update.invite_link {update.invite_link}")
            if update.invite_link and update.invite_link.invite_link:
                referral_code = update.invite_link.invite_link.split('/')[-1]
                logger.info(f"New member {referred_id} joined via invite link {referral_code}")

                # Проверяем, связана ли инвайт-ссылка с каким-либо giveaway
                cursor.execute("SELECT user_id, giveaway FROM ref_links_giveaway WHERE referral_link = %s", (referral_code,))
                referrer = cursor.fetchone()
                if referrer:
                    referrer_id, giveaway_id = referrer
                    name = update.new_chat_member.user.first_name
                    if update.new_chat_member.user.last_name:
                        if update.new_chat_member.user.last_name != " ":
                            name = " " + update.new_chat_member.user.last_name
                    try:
                        username = update.new_chat_member.user.username 
                    except Exception as e:
                        username = ""
                    try:
                        # Добавляем нового пользователя
                        cursor.execute("""
                            INSERT INTO users (user_id, name, username, referral_link, interacted)
                            VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT (user_id) DO NOTHING
                        """, (referred_id, name, username, referral_code, False))

                        # Обновляем количество рефералов
                        cursor.execute("UPDATE ref_links_giveaway SET referrals_count = referrals_count + 1 WHERE referral_link = %s", (referral_code,))
                        new_count = cursor.fetchone()[0]

                        # Добавляем запись в giveaway_records
                        cursor.execute("""
                            INSERT INTO giveaway_records (creator_id, referred_id, referral_link_id, giveaway_id, created_at)
                            VALUES (%s, %s, (SELECT id FROM ref_links_giveaway WHERE referral_link = %s), %s, CURRENT_TIMESTAMP)
                        """, (referrer_id, referred_id, referral_code, giveaway_id))

                        conn.commit()
                        logger.info(f"User {referred_id} was giveaway referred by user {referrer_id} for giveaway {giveaway_id}, new referral count: {new_count}")
                    except Exception as e:
                        logger.error(f"Failed to insert giveaway referral for {referred_id}: {e}")
                        conn.rollback()
                else:
                    logger.info(f"No giveaway referrer found for invite link {update.invite_link.invite_link}")
            else:
                logger.info("Invite link is missing in the update")
    except Exception as e:
        logger.info(f"{e}")

# Функция для периодического выполнения первой задачи
# это должна быть функция для проверки
def periodic_task_1():
    while True:
        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        print(f"Запуск первой периодической задачи в {current_time}...")
        print(f"Первая задача выполнена в {current_time}.")
        time.sleep(300)  # Пауза 5 минут (300 секунд)

# Функция для периодического выполнения второй задачи
# это должна быть задача для проверки времени с момента создания розыгрыша
def periodic_task_2():
    while True:
        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        print(f"Запуск второй периодической задачи в {current_time}...")
        print(f"Вторая задача выполнена в {current_time}.")
        time.sleep(60)  # Пауза 1 минута (60 секунд)

def update_or_create_user(cursor, user_id, name, username):
    try:
        cursor.execute("""
            INSERT INTO users (user_id, name, username, interacted)
            VALUES (%s, %s, %s, TRUE)
            ON CONFLICT (user_id) DO UPDATE SET interacted = TRUE
        """, (user_id, name, username))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()  # Откат транзакции в случае ошибки
        return False
    finally:
        return True

def get_giveaway_details(giveaway_id):
    """ Получает название канала и название розыгрыша по идентификатору розыгрыша. """
    try:
        cursor.execute("""
            SELECT g.name AS giveaway_name, c.title AS channel_title
            FROM giveaways g
            JOIN chats c ON g.chat_id = c.chat_id
            WHERE g.giveaway_id = %s
        """, (giveaway_id,))
        result = cursor.fetchone()
        if result:
            giveaway_name, channel_title = result
            return {'giveaway_name': giveaway_name, 'channel_title': channel_title}
        else:
            return {'giveaway_name': None, 'channel_title': None}
    except Exception as e:
        print(f"Ошибка при получении данных розыгрыша: {e}")
        return {'giveaway_name': None, 'channel_title': None}

# Хэндлер для команды "Начать"
@app.on_message(filters.text & filters.create(lambda _, __, message: message.text == "Начать"))
def start(client, message: Message):
    logger.info(f"{message.text}")
    user_id = message.from_user.id
    user_selection_active[message.from_user.id] = False
    name = message.from_user.first_name
    if message.from_user.last_name:
        if message.from_user.last_name != " ":
            name = " " + message.from_user.last_name
    try:
        username = message.from_user.username 
    except Exception as e:
        username = ""
    update_or_create_user(cursor, user_id, name, username)
    user_data = load_user_data(user_id)
    if "user_state" not in user_data:
        # Инициализация данных пользователя
        SET_STATE(user_id, MAIN_MENU_STATE)
        message.reply("Добро пожаловать! Вы зарегистрированы.", reply_markup=main_menu_buttons())
    else:
        message.reply("Вы уже зарегистрированы.", reply_markup=main_menu_buttons())

@app.on_message(filters.command("start"))
def start(client, message: Message):
    logger.info(f"{message.text}")
    user_id = message.from_user.id
    user_selection_active[message.from_user.id] = False
    name = message.from_user.first_name
    if message.from_user.last_name:
        if message.from_user.last_name != " ":
            name = " " + message.from_user.last_name
    try:
        username = message.from_user.username 
    except Exception as e:
        username = ""
    update_or_create_user(cursor, user_id, name, username)
    # Разбор параметра из команды
    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        param = args[1]
    else:
        param = None

    if param and param.startswith('giveaway_'):
        giveaway_id = param.split('_')[1]
        giveaway_name, channel_name = get_giveaway_details(int(giveaway_id))
        SET_STATE(user_id, MAIN_MENU_STATE)
        message.reply("Добро пожаловать! Теперь вы можете учавствовать в розыгрыше "+giveaway_name+" на канале "+channel_name+"!", reply_markup=main_menu_buttons())
    else:
        user_data = load_user_data(user_id)
        if "user_state" not in user_data:
            # Инициализация данных пользователя
            SET_STATE(user_id, MAIN_MENU_STATE)
            message.reply("Добро пожаловать! Вы зарегистрированы.", reply_markup=main_menu_buttons())
        else:
            message.reply("Вы уже зарегистрированы.", reply_markup=main_menu_buttons())

# Хэндлер для основного меню
@app.on_message(filters.text & filters.create(lambda _, __, message: message.text in ["Реферальные ссылки", "Лидерборд", "Мои рефералы", "О боте"] and USER_STATE(GET_STATE(message.from_user.id))))
def main_menu(client, message: Message):
    logger.info(f"{message.text}")
    user_id = message.from_user.id
    user_data = load_user_data(user_id)
    if "user_state" not in user_data:
        message.reply("Вы не зарегистрированы. Нажмите 'Начать' для регистрации.", reply_markup=start_button())
        return

    if message.text == "Реферальные ссылки":
        SET_STATE(user_id, REFERRAL_LINKS_STATE)
        giveaways_list = get_giveaways_from_db()
        message.reply("Доступные розыгрыши: ...", reply_markup=create_universal_keyboard(user_id, giveaways_list, 1, "giveaway", "name"))
    elif message.text == "Лидерборд":
        SET_STATE(user_id, LEADERBOARD_STATE)
        message.reply("Лидерборд: ...", reply_markup=back_button())
    elif message.text == "Мои рефералы":
        SET_STATE(user_id, MY_REFERRALS_STATE)
        message.reply("Ваши рефералы: ...", reply_markup=back_button())
    elif message.text == "О боте":
        SET_STATE(user_id, ABOUT_BOT_STATE)
        message.reply("Информация о боте: ...", reply_markup=about_bot_buttons())

# Хэндлер для админ панели
@app.on_message(filters.text & filters.create(lambda _, __, message: message.text in ["Розыгрыши", "Выйти с режима администратора", "О боте"] and ADMIN_STATE(GET_STATE(message.from_user.id))))
def admin_panel(client, message: Message):
    logger.info(f"{message.text}")
    user_id = message.from_user.id
    user_data = load_user_data(user_id)
    if "user_state" not in user_data:
        message.reply("Вы не зарегистрированы. Нажмите 'Начать' для регистрации.", reply_markup=start_button())
        return

    if message.text == "Розыгрыши":
        SET_STATE(user_id, ADMIN_GIVEAWAYS_STATE)
        message.reply("Управление розыгрышами: ...", reply_markup=create_giveaway_buttons())
    elif message.text == "Выйти с режима администратора":
        SET_STATE(user_id, MAIN_MENU_STATE)
        message.reply("Вы вернулись в главное меню.", reply_markup=main_menu_buttons())
    elif message.text == "О боте":
        SET_STATE(user_id, ABOUT_BOT_STATE_ADMIN)
        message.reply("Информация о боте: ...", reply_markup=about_bot_admin_buttons())

# Хэндлер для перехода в админскую панель из "О боте"
@app.on_message(filters.text & filters.create(lambda _, __, message: message.text == "Перейти в админскую панель" and GET_STATE(message.from_user.id) == ABOUT_BOT_STATE))
def go_to_admin_panel(client, message: Message):
    logger.info(f"{message.text}")
    user_id = message.from_user.id
    SET_STATE(user_id, ADMIN_PANEL_STATE)
    message.reply("Добро пожаловать в админскую панель.", reply_markup=admin_panel_buttons())

# Хэндлер для "Назад" из "О боте" в админском режиме
@app.on_message(filters.text & filters.create(lambda _, __, message: message.text == "Выйти с режима админа" and GET_STATE(message.from_user.id) == ABOUT_BOT_STATE_ADMIN))
def back_from_about(client, message: Message):
    logger.info(f"{message.text}")
    user_id = message.from_user.id
    SET_STATE(user_id, MAIN_MENU_STATE)
    message.reply("Вы вернулись в главное меню.", reply_markup=main_menu_buttons())

# Хэндлер для "Назад" из "О боте"
@app.on_message(filters.text & filters.create(lambda _, __, message: message.text == "Назад" and ADMIN_STATE(GET_STATE(message.from_user.id))))
def back_from_about(client, message: Message):
    logger.info(f"{message.text}")
    user_id = message.from_user.id
    SET_STATE(user_id, ADMIN_PANEL_STATE)
    message.reply("Вы вернулись в админ панель.", reply_markup=admin_panel_buttons())

# Основной эндлер для "Назад"
@app.on_message(filters.text & filters.create(lambda _, __, message: message.text == "Назад"))
def back_from_about(client, message: Message):
    logger.info(f"{message.text}")
    user_id = message.from_user.id
    SET_STATE(user_id, MAIN_MENU_STATE)
    message.reply("Вы вернулись в главное меню.", reply_markup=main_menu_buttons())

# Хэндлер для открытия управления розыгрышами
@app.on_message(filters.text & filters.create(lambda _, __, message: GET_STATE(message.from_user.id) == ADMIN_GIVEAWAYS_STATE))
def create_giveaway(client, message: Message):
    logger.info(f"{message.text}")
    user_id = message.from_user.id

    if message.text == "Назад":
        SET_STATE(user_id, ADMIN_PANEL_STATE)
        message.reply("Вы вернулись в админ панель.", reply_markup=admin_panel_buttons())
    elif "Создать розыгрыш" in message.text:
        SET_STATE(user_id, GIVEAWAY_NAME_SET)
        message.reply("Укажите название розыгрыша:", reply_markup=back_button())
    else:
        message.reply("Неправильная ссылка. Пожалуйста, попробуйте еще раз или нажмите 'Назад'.", reply_markup=back_button())

#GIVEAWAY_NAME_SET
# Хэндлер для выбора имени розыгрыша
@app.on_message(filters.text & filters.create(lambda _, __, message: GET_STATE(message.from_user.id) == GIVEAWAY_NAME_SET))
def set_duration(client, message: Message):
    logger.info(f"{message.text}")
    user_id = message.from_user.id

    if message.text == "Назад":
        SET_STATE(user_id, ADMIN_GIVEAWAYS_STATE)
        message.reply("Управление розыгрышами: ...", reply_markup=back_button())
    elif message.text:
        
        #user_data[user_id] = {"giveaway_name": message.text}
        clean_value = clean_text(message.text)
        SET_PROPERTY(user_id, "giveaway_name", clean_value)
        SET_STATE(user_id, CREATE_GIVEAWAY_LINK)
        user_selection_active[message.from_user.id] = True
        if len(get_channels_from_db()) > 0:
            message.reply(f"Выберите канал:", reply_markup=create_channel_keyboard(1))
        else:
            message.reply("Чатов нет.", reply_markup=back_button())
    else:
        message.reply("Неправильный выбор. Пожалуйста, выберите часы или дни.", reply_markup=duration_buttons())


# Хэндлер для создания розыгрыша в админ панели
@app.on_message(filters.text & filters.create(lambda _, __, message: GET_STATE(message.from_user.id) == CREATE_GIVEAWAY_LINK))
def create_giveaway(client, message: Message):
    logger.info(f"{message.text}")
    user_id = message.from_user.id

    if message.text == "Назад":
        SET_STATE(user_id, ADMIN_PANEL_STATE)
        message.reply("Вы вернулись в админ панель.", reply_markup=admin_panel_buttons())
    elif "Продолжить" in message.text:
        SET_STATE(user_id, SET_DURATION_STATE)
        message.reply(f"Выберите количество (часы, дни):", reply_markup=duration_buttons())
    else:
        message.reply("Неправильная ссылка. Пожалуйста, попробуйте еще раз или нажмите 'Назад'.", reply_markup=back_button())

# Хэндлер для выбора продолжительности розыгрыша
@app.on_message(filters.text & filters.create(lambda _, __, message: GET_STATE(message.from_user.id) == SET_DURATION_STATE))
def set_duration(client, message: Message):
    logger.info(f"{message.text}")
    user_id = message.from_user.id

    if message.text == "Назад":
        SET_STATE(user_id, ADMIN_GIVEAWAYS_STATE)
        message.reply("Управление розыгрышами: ...", reply_markup=back_button())
    elif message.text in ["Часы", "Дни"]:
        #user_data[user_id]["duration_type"] = message.text
        clean_value = clean_text(message.text)
        SET_PROPERTY(user_id, "duration_type", clean_value)
        SET_STATE(user_id, INPUT_DURATION_STATE)
        message.reply(f"Введите количество {message.text.lower()}:")
    else:
        message.reply("Неправильный выбор. Пожалуйста, выберите часы или дни.", reply_markup=duration_buttons())

# Хэндлер для ввода продолжительности розыгрыша
@app.on_message(filters.text & filters.create(lambda _, __, message: GET_STATE(message.from_user.id) == INPUT_DURATION_STATE))
def input_duration(client, message: Message):
    logger.info(f"{message.text}")
    user_id = message.from_user.id

    if message.text == "Назад":
        SET_STATE(user_id, SET_DURATION_STATE)
        message.reply("Укажите продолжительность розыгрыша (выберите часы или дни):", reply_markup=duration_buttons())
    elif message.text.isdigit():
        #user_data[user_id]["duration"] = int(message.text)
        clean_value = clean_text(message.text)
        SET_PROPERTY(user_id, "duration", clean_value)
        SET_STATE(user_id, SET_PRIZES_STATE)
        message.reply("Введите призы и количество мест:\n\n Призы пишутся в следующем формате:\n\n1-5; воздушный шарик\n6-10; леденец\n11-000; скидка 10%\n0; раффл 5$ долларов; 10\n\nпервая часть параметров - призовые места в ТОП\nвторая часть параметров - название приза\nтретья часть параметров (опционально) - минимальное количество приглашённых друзей")
    else:
        message.reply(f"Неправильный ввод. Введите количество {(GET_PROPERTY(user_id, 'duration_type')).lower()} цифрами.")

# Хэндлер для ввода призов
@app.on_message(filters.text & filters.create(lambda _, __, message: GET_STATE(message.from_user.id) == SET_PRIZES_STATE))
def set_prizes(client, message: Message):
    logger.info(f"{message.text}")
    user_id = message.from_user.id

    if message.text == "Назад":
        SET_STATE(user_id, INPUT_DURATION_STATE)
        message.reply(f"Введите количество {GET_PROPERTY(user_id, 'duration_type').lower()}:")
    else:
        #user_data[user_id]["prizes"] = message.text
        clean_value = clean_text(message.text)
        SET_PROPERTY(user_id, "prizes", clean_value)
        SET_STATE(user_id, POST_GIVEAWAY_STATE)
        giveaway, id = DB_create_giveaway(user_id, GET_PROPERTY(user_id, "giveaway_channel_id"), GET_PROPERTY(user_id, "giveaway_name"), GET_PROPERTY(user_id, "duration_type"), GET_PROPERTY(user_id, "duration"), GET_PROPERTY(user_id, "prizes"))
        if giveaway is False and id == -500:
            message.reply("Ошибка при создании розыгрыша", reply_markup=back_button())
        elif giveaway is False and id:
            message.reply(f"Для канала существует розыгрыш {id})", reply_markup=back_button())
        elif giveaway is True and id:
            message.reply(f"Розыгрыш {id} успешно создан. Теперь вы можете вернуться в главное меню.", reply_markup=back_button())
        else:
            message.reply(f"Ошибка", reply_markup=back_button())

# Хэндлер для обработки случайных сообщений
@app.on_message(filters.text & ~filters.command("start"))
def handle_random_messages(client, message: Message):
    logger.info(f"{message.text}")
    user_id = message.from_user.id
    user_data = load_user_data(user_id)
    if "user_state" not in user_data:
        message.reply("Вы не зарегистрированы. Нажмите 'Начать' для регистрации.", reply_markup=start_button())
    else:
        if (ADMIN_STATE(GET_STATE(message.from_user.id))):
            message.reply("Неправильный ввод. Пожалуйста, используйте кнопки админ панели.", reply_markup=admin_panel_buttons())
        else:
            message.reply("Неправильный ввод. Пожалуйста, используйте кнопки меню.", reply_markup=main_menu_buttons()) 

if __name__ == "__main__":
    task_1_thread = threading.Thread(target=periodic_task_1)
    task_2_thread = threading.Thread(target=periodic_task_2)
    
    task_1_thread.daemon = True  # Позволяет завершить поток при выходе из программы
    task_2_thread.daemon = True  # Позволяет завершить поток при выходе из программы
    
    task_1_thread.start()
    task_2_thread.start()
    
    app.run()