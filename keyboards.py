from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="📦 Каталог", callback_data="catalog:0")
    kb.button(text="🗂 По категориям", callback_data="categories")
    kb.button(text="📏 Гайды по размерам", callback_data="guides")
    kb.adjust(1)
    return kb.as_markup()


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

    kb.row(InlineKeyboardButton(text="⬅️ В меню", callback_data="menu"))
    return kb.as_markup()


def guides_list_kb(guides):
    kb = InlineKeyboardBuilder()
    for g in guides:
        kb.button(text=g["brand"], callback_data=f"guide:{g['id']}")
    kb.adjust(2)
    kb.row(InlineKeyboardButton(text="⬅️ В меню", callback_data="menu"))
    return kb.as_markup()


def categories_kb(categories):
    kb = InlineKeyboardBuilder()
    for c in categories:
        kb.button(text=c, callback_data=f"cat:{c}")
    kb.adjust(2)
    kb.row(InlineKeyboardButton(text="⬅️ В меню", callback_data="menu"))
    return kb.as_markup()


def sizes_kb(sizes):
    kb = InlineKeyboardBuilder()
    kb.button(text="Все размеры", callback_data="catsize:all")
    for s in sizes:
        kb.button(text=s, callback_data=f"catsize:{s}")
    kb.adjust(3)
    kb.row(InlineKeyboardButton(text="⬅️ К категориям", callback_data="categories"))
    return kb.as_markup()


def filtered_item_kb(listing, index, total, category):
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

    kb.row(InlineKeyboardButton(text="⬅️ К размерам", callback_data=f"cat:{category}"))
    kb.row(InlineKeyboardButton(text="⬅️ В меню", callback_data="menu"))
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