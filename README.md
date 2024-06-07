# Telegram Referral Bot

Этот бот предназначен для генерации уникальных реферальных ссылок на каналы и подсчета количества новых участников, которые перешли по этим ссылкам.

## Настройка и запуск

### Требования

- Python 3.8 или выше
- PostgreSQL
- Virtualenv

### Установка

1. Клонируйте репозиторий: 
   ```sh
   git clone https://github.com/tvirgg/inv_bot.git
   cd inv_bot
### Создайте и активируйте виртуальное окружение:


python -m venv venv
source venv/bin/activate  # Для Windows: venv\Scripts\activate
Установите необходимые зависимости:


 pip install -r requirements.txt



### Создайте базу данных PostgreSQL и таблицы:

-- Создание таблиц users и referrals с учетом channel_id
CREATE TABLE users (
    user_id BIGINT PRIMARY KEY,
    username TEXT,
    referral_link TEXT,
    referrals_count INTEGER DEFAULT 0
);

CREATE TABLE referrals (
    referral_id SERIAL PRIMARY KEY,
    referrer_id BIGINT REFERENCES users(user_id),
    referred_id BIGINT REFERENCES users(user_id),
    channel_id TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Предоставление привилегий пользователю bot_user
GRANT ALL PRIVILEGES ON TABLE users TO bot_user;
GRANT ALL PRIVILEGES ON TABLE referrals TO bot_user;


### env

API_ID=your_api_id 
API_HASH=your_api_hash 
BOT_TOKEN=your_bot_token 
DB_NAME=your_db_name 
DB_USER=your_db_user 
DB_PASS=your_db_password 
DB_HOST=your_db_host 
DB_PORT=your_db_port


### Активируйте виртуальное окружение, если оно еще не активировано:

source venv/bin/activate  # Для Windows: venv\Scripts\activate


### Запустите бота:

python bot.py
Пример использования
Запустите бота в Telegram и используйте команду /start с ссылкой на канал для генерации реферальной ссылки:

/start https://t.me/your_channel
Перейдите по сгенерированной реферальной ссылке, чтобы присоединиться к каналу и быть учтенным как новый участник.
/stats  - статы
    
