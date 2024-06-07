import logging
from pyrogram import Client, filters
from pyrogram.types import Message, ChatMemberUpdated
import psycopg2
import os
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

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

# Функция для генерации реферальной ссылки
def generate_referral_link(channel_id, user_id):
    return f"https://t.me/{channel_id}?start={user_id}"

# Генерация реферальной ссылки для указанного канала
@app.on_message(filters.command("start"))
def start(client, message: Message):
    if len(message.command) < 2:
        message.reply("Пожалуйста, укажите ссылку на канал.")
        return
    
    channel_id = message.command[1].replace("https://t.me/", "").replace("/", "")
    user_id = message.from_user.id
    
    cursor.execute("INSERT INTO users (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING", (user_id,))
    conn.commit()
    
    referral_link = generate_referral_link(channel_id, user_id)
    message.reply(f"Ваша реферальная ссылка: {referral_link}")
    logger.info(f"User {user_id} generated referral link for channel {channel_id}")

# Отслеживание переходов по реферальной ссылке
@app.on_message(filters.regex(r"start=(\d+)"))
def referral_start(client, message: Message):
    referrer_id = int(message.matches[0].group(1))
    referred_id = message.from_user.id

    # Проверка, что это не тот же самый пользователь
    if referrer_id == referred_id:
        message.reply("Вы не можете пригласить сами себя.")
        return
    
    cursor.execute("INSERT INTO users (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING", (referred_id,))
    cursor.execute("INSERT INTO referrals (referrer_id, referred_id, channel_id) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING", (referrer_id, referred_id, message.chat.id))
    conn.commit()

    cursor.execute("SELECT * FROM referrals WHERE referrer_id = %s AND referred_id = %s AND channel_id = %s", (referrer_id, referred_id, message.chat.id))
    referral = cursor.fetchone()
    if referral:
        logger.info(f"Referral entry created: {referral}")
    else:
        logger.error(f"Failed to create referral entry for referrer {referrer_id} and referred {referred_id}")

    cursor.execute("UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id = %s RETURNING referrals_count", (referrer_id,))
    new_count = cursor.fetchone()[0]
    
    message.reply(f"Вы были приглашены пользователем с ID: {referrer_id}")
    logger.info(f"User {referred_id} was referred by user {referrer_id}, new referral count for {referrer_id}: {new_count}")

# Отслеживание новых участников канала
@app.on_chat_member_updated()
def track_new_members(client, update: ChatMemberUpdated):
    if update.new_chat_member:
        referred_id = update.new_chat_member.user.id
        logger.info(f"Member detected: {referred_id}")

        cursor.execute("SELECT referrer_id FROM referrals WHERE referred_id = %s", (referred_id,))
        referrer = cursor.fetchone()
        if referrer:
            referrer_id = referrer[0]
            logger.info(f"Referrer found: {referrer_id}")

            cursor.execute("UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id = %s RETURNING referrals_count", (referrer_id,))
            new_count = cursor.fetchone()[0]

            logger.info(f"Updated referral count for referrer {referrer_id}: {new_count}")
            conn.commit()
        else:
            logger.info(f"No referrer found for member {referred_id}")
    else:
        logger.error("new_chat_member is None")

# Вывод лидерского дашборда
@app.on_message(filters.command("leaderboard"))
def leaderboard(client, message: Message):
    cursor.execute("SELECT user_id, referrals_count FROM users ORDER BY referrals_count DESC LIMIT 10")
    leaderboard = cursor.fetchall()
    
    response = "🏆 Топ пользователей по приглашениям:\n\n"
    for idx, (user_id, referrals_count) in enumerate(leaderboard, 1):
        response += f"{idx}. Пользователь {user_id}: {referrals_count} приглашений\n"
    
    message.reply(response)

# Личный кабинет пользователя для отслеживания количества приглашенных
@app.on_message(filters.command("stats"))
def stats(client, message: Message):
    user_id = message.from_user.id
    cursor.execute("SELECT referrals_count FROM users WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()
    referrals_count = result[0] if result else 0
    
    message.reply(f"Вы пригласили {referrals_count} пользователей.")
    logger.info(f"User {user_id} checked their stats")

# Запуск бота
app.run()
