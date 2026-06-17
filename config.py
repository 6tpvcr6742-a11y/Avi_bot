import os

# Токен бота, который выдаёт @BotFather в Telegram.
# Задаётся через переменную окружения BOT_TOKEN (см. README.md)
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Твой Telegram ID — только у этого пользователя будет доступ к админ-командам
# (/add, /addguide, /mylistings). Узнать свой ID можно у бота @userinfobot.
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

DB_PATH = os.getenv("DB_PATH", "shop.db")
