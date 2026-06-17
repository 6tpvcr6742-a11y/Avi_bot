from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="📦 Каталог", callback_data="catalog:0")
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


def admin_listings_kb(listings):
    kb = InlineKeyboardBuilder()
    for l in listings:
        kb.button(text=f"❌ Удалить #{l['id']}: {l['title'][:25]}", callback_data=f"del:{l['id']}")
    kb.adjust(1)
    return kb.as_markup()
