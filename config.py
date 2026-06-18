import os

# Токен бота, который выдаёт @BotFather в Telegram.
# Задаётся через переменную окружения BOT_TOKEN (см. README.md)
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Telegram ID администраторов — только у них доступ к админ-командам
# (/add, /addguide, /mylistings, /edit). Узнать свой ID можно у бота @userinfobot.
# Можно указать несколько ID через запятую, например: 111111111,222222222
_raw_admin_ids = os.getenv("ADMIN_ID", "0")
ADMIN_IDS = {int(x.strip()) for x in _raw_admin_ids.split(",") if x.strip()}

# На Bothost постоянное хранилище для бота доступно через переменную DATA_DIR
# (например /app/data) — она переживает редеплой/перезапуск, в отличие от
# обычной временной папки проекта. SHARED_DIR — отдельная вещь (общие файлы
# на весь аккаунт), на неё тоже проверяем на случай, если она пригодится.
_persistent_dir = os.getenv("DATA_DIR") or os.getenv("SHARED_DIR") or ""
DB_PATH = os.getenv("DB_PATH") or (
    os.path.join(_persistent_dir, "shop.db") if _persistent_dir else "shop.db"
)