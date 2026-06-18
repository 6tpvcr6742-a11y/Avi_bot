import os

# Токен бота, который выдаёт @BotFather в Telegram.
# Задаётся через переменную окружения BOT_TOKEN (см. README.md)
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Telegram ID администраторов — только у них доступ к админ-командам
# (/add, /addguide, /mylistings, /edit). Узнать свой ID можно у бота @userinfobot.
# Можно указать несколько ID через запятую, например: 111111111,222222222
_raw_admin_ids = os.getenv("ADMIN_ID", "0")
ADMIN_IDS = {int(x.strip()) for x in _raw_admin_ids.split(",") if x.strip()}

# Если на Bothost включено «Общее хранилище» — база будет лежать там
# (путь /app/shared, переменная SHARED_DIR), и переживёт редеплой/перезапуск.
# Если хранилище не включено, база лежит в обычной (временной) папке проекта.
_shared_dir = os.getenv("SHARED_DIR", "")
DB_PATH = os.getenv("DB_PATH") or (
    os.path.join(_shared_dir, "shop.db") if _shared_dir else "shop.db"
)