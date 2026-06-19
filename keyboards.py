from aiogram.types import InlineKeyboardButton, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def main_reply_kb():
    kb = ReplyKeyboardBuilder()
    kb.button(text="📦 Каталог")
    kb.button(text="🗂 По категориям")
    kb.button(text="📏 Гайды по размерам")
    kb.adjust(2, 1)
    return kb.as_markup(resize_keyboard=True)


def categories_reply_kb(categories):
    kb = ReplyKeyboardBuilder()
    for c in categories:
        kb.button(text=c)
    kb.adjust(2)
    kb.row(KeyboardButton(text="⬅️ Главное меню"))
    return kb.as_markup(resize_keyboard=True)


def sizes_reply_kb(sizes):
    kb = ReplyKeyboardBuilder()
    kb.button(text="Все размеры")
    for s in sizes:
        kb.button(text=s)
    kb.adjust(3)
    kb.row(KeyboardButton(text="⬅️ Назад"), KeyboardButton(text="⬅️ Главное меню"))
    return kb.as_markup(resize_keyboard=True)


def guides_reply_kb(guides):
    kb = ReplyKeyboardBuilder()
    for g in guides:
        kb.button(text=g["brand"])
    kb.adjust(2)
    kb.row(KeyboardButton(text="⬅️ Главное меню"))
    return kb.as_markup(resize_keyboard=True)


def back_to_menu_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ В меню", callback_data="menu")
    return kb.as_markup()


def catalog_item_kb(listing, index, total):
    kb = InlineKeyboardBuilder()
    row = []
    if index > 0:
        row.append(InlineKeyboardButton(text="⬅️", callback_data=f"catalog:{index-1}"))
    row.append(InlineKeyboardButton(text=f"{index+1}/{total}", callback_data="noop"))
    if index < total - 1:
        row.append(InlineKeyboardButton(text="➡️", callback_data=f"catalog:{index+1}"))
    kb.row(*row)

    kb.row(InlineKeyboardButton(text="🛒 Смотреть и написать на Avito", url=listing["avito_url"]))

    if listing["brand"]:
        kb.row(InlineKeyboardButton(text="📏 Узнать свой размер", callback_data=f"guide_for:{listing['brand']}"))

    return kb.as_markup()


def filtered_item_kb(listing, index, total):
    kb = InlineKeyboardBuilder()
    row = []
    if index > 0:
        row.append(InlineKeyboardButton(text="⬅️", callback_data=f"catpage:{index-1}"))
    row.append(InlineKeyboardButton(text=f"{index+1}/{total}", callback_data="noop"))
    if index < total - 1:
        row.append(InlineKeyboardButton(text="➡️", callback_data=f"catpage:{index+1}"))
    kb.row(*row)

    kb.row(InlineKeyboardButton(text="🛒 Смотреть и написать на Avito", url=listing["avito_url"]))

    if listing["brand"]:
        kb.row(InlineKeyboardButton(text="📏 Узнать свой размер", callback_data=f"guide_for:{listing['brand']}"))

    kb.row(InlineKeyboardButton(text="⬅️ К размерам", callback_data="backsizes"))
    return kb.as_markup()


def admin_listings_kb(listings):
    kb = InlineKeyboardBuilder()
    for l in listings:
        kb.button(text=f"❌ Удалить #{l['id']}: {l['title'][:25]}", callback_data=f"del:{l['id']}")
    kb.adjust(1)
    return kb.as_markup()


def edit_listings_kb(listings):
    kb = InlineKeyboardBuilder()
    for l in listings:
        kb.button(text=f"#{l['id']}: {l['title'][:30]}", callback_data=f"editsel:{l['id']}")
    kb.adjust(1)
    return kb.as_markup()


EDIT_FIELDS = {
    "title": "Название",
    "price": "Цена",
    "description": "Описание",
    "avito_url": "Ссылка на Avito",
    "brand": "Бренд",
    "category": "Категория",
    "size": "Размер",
    "photo_id": "Фото",
}


def edit_fields_kb(listing_id):
    kb = InlineKeyboardBuilder()
    for field, label in EDIT_FIELDS.items():
        kb.button(text=label, callback_data=f"editfield:{listing_id}:{field}")
    kb.adjust(2)
    return kb.as_markup()