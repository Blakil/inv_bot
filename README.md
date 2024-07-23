# Telegram Giveaway Bot

Этот бот на базе Pyrogram предназначен для управления розыгрышами в Telegram-каналах. Пользователи могут создавать розыгрыши, участвовать в них через реферальные ссылки, а администраторы могут управлять розыгрышами через специальную панель.

## Настройка и запуск

### Требования

- Python 3.8 или выше
- PostgreSQL
- Virtualenv

### Установка

1. Клонируйте репозиторий: 
   ```sh
   git clone https://github.com/tvirgg/inv_bot.git
   cd inv_bot``
## Создайте и активируйте виртуальное окружение:

python -m venv venv

# Для Linux: source venv/bin/activate  
# Для Windows: venv\Scripts\activate

### Установите необходимые зависимости:
```sh
pip install -r requirements.txt
```


## Создайте базу данных PostgreSQL и таблицы:

-- Создание таблиц users и referrals с учетом channel_id
```sh

CREATE TABLE chats (
    chat_id BIGINT PRIMARY KEY,
    title TEXT,
    username TEXT,
    accessible BOOLEAN
);
CREATE TABLE users (
    user_id BIGINT PRIMARY KEY,
    name TEXT,
    username TEXT,
    referral_link TEXT,
    interacted BOOLEAN DEFAULT false
);


CREATE TABLE giveaways (
    giveaway_id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id),
    chat_id BIGINT REFERENCES chats(chat_id),
    name TEXT,
    duration_type TEXT,
    duration INTEGER,
    prizes TEXT
);

CREATE TABLE ref_links_giveaway (
    referral_link TEXT PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id),
    name TEXT,
    channel_id BIGINT REFERENCES chats(chat_id),
    giveaway SERIAL REFERENCES giveaways(giveaway_id),
    referrals_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed BOOLEAN DEFAULT FALSE
);

CREATE TABLE giveaway_records (
    id SERIAL PRIMARY KEY,
    creator_id BIGINT REFERENCES users(user_id),
    referred_id BIGINT REFERENCES users(user_id),
    referral_link TEXT REFERENCES ref_links_giveaway(referral_link),
    giveaway_id SERIAL REFERENCES giveaways(giveaway_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

GRANT ALL PRIVILEGES ON TABLE ref_links_giveaway TO bot_user;
GRANT ALL PRIVILEGES ON TABLE chats TO bot_user;
GRANT ALL PRIVILEGES ON TABLE giveaways TO bot_user;
GRANT ALL PRIVILEGES ON TABLE giveaway_records TO bot_user;
GRANT ALL PRIVILEGES ON TABLE users TO bot_user;


#not used
#CREATE TABLE referrals (
#    referral_id BIGINT PRIMARY KEY,
#    referrer_id BIGINT REFERENCES users(user_id),
#    referrer_link TEXT,
#    channel_id TEXT,
#   timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#);

-- Предоставление привилегий пользователю bot_user
GRANT ALL PRIVILEGES ON TABLE users TO bot_user;
GRANT ALL PRIVILEGES ON TABLE referrals TO bot_user;
```

## env
```sh
API_ID=your_api_id 
API_HASH=your_api_hash 
BOT_TOKEN=your_bot_token 
DB_NAME=your_db_name 
DB_USER=your_db_user 
DB_PASS=your_db_password 
DB_HOST=your_db_host 
DB_PORT=your_db_port
```

## Активируйте виртуальное окружение, если оно еще не активировано:
```sh
source venv/bin/activate  # Для Windows: venv\Scripts\activate
```

## Запустите бота:

python bot.py

## Основные функции

1. **Инициализация и настройки**:
   - Загрузка переменных окружения.
   - Настройка логирования.
   - Инициализация клиента Pyrogram и подключение к базе данных PostgreSQL.

2. **Управление пользователями и состояниями**:
   - Функции для управления состоянием пользователей (`GET_STATE`, `SET_STATE`, `GET_PROPERTY`, `SET_PROPERTY`).
   - Функции для загрузки и сохранения данных пользователей в файл (`save_user_data`, `load_user_data`, `load_all_data`).

3. **Создание и управление розыгрышами**:
   - Функции для создания розыгрышей и добавления каналов в базу данных (`DB_create_giveaway`, `DB_add_chat`).
   - Обработчики сообщений и callback-запросов для управления розыгрышами.

4. **Периодические задачи**:
   - Периодические задачи для проверки розыгрышей и выполнения других фоновых задач.

5. **Интерфейсы и кнопки**:
   - Функции для создания различных типов кнопок и клавиатур.
   - Обработчики сообщений и callback-запросов для работы с кнопками и клавиатурами.

## Пример использования

1. **Регистрация пользователя**:
   - Отправьте команду `/start` или нажмите кнопку "Начать" для регистрации.

2. **Управление розыгрышами**:
   - Для пользователей: выберите "Реферальные ссылки", "Лидерборд", "Мои рефералы" или "О боте".
   - Для администраторов: выберите "Розыгрыши", "Выйти с режима администратора" или "О боте".

3. **Создание розыгрыша**:
   - Войдите в админ-панель и выберите "Создать розыгрыш".
   - Укажите название розыгрыша, выберите канал, установите продолжительность и добавьте призы.

## Файл requirements.txt

```plaintext
pyrogram==2.0.106
psycopg2-binary==2.9.3
python-dotenv==0.19.2
```

Эти зависимости необходимы для работы бота и взаимодействия с базой данных PostgreSQL. Убедитесь, что все пакеты установлены, прежде чем запускать бота.