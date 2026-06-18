import asyncio
import logging

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

import config
import database as db
import keyboards as kb

logging.basicConfig(level=logging.INFO)

router = Router()

# Telegram ограничивает подпись к фото 1024 символами, в это же число входят
# название и цена. Поэтому держим описание заметно короче этого лимита.
MAX_DESCRIPTION_LEN = 700


def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


# ===================== FSM: добавление товара =====================

class AddListing(StatesGroup):
    url = State()
    title = State()
    price = State()
    description = State()
    brand = State()
    photo = State()


@router.message(Command("add"))
async def add_listing_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(AddListing.url)
    await message.answer(
        "Добавляем новый товар.\n\nПришли ссылку на объявление на Avito.\n/cancel — отменить"
    )


@router.message(Command("cancel"))
async def cancel_any(message: Message, state: FSMContext):
    if await state.get_state() is None:
        return
    await state.clear()
    await message.answer("Отменено.")


@router.message(AddListing.url)
async def add_listing_url(message: Message, state: FSMContext):
    await state.update_data(avito_url=message.text.strip())
    await state.set_state(AddListing.title)
    await message.answer("Название товара (как будет видно покупателю):")


@router.message(AddListing.title)
async def add_listing_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(AddListing.price)
    await message.answer("Цена (например: 2 500 ₽):")


@router.message(AddListing.price)
async def add_listing_price(message: Message, state: FSMContext):
    await state.update_data(price=message.text.strip())
    await state.set_state(AddListing.description)
    await message.answer("Краткое описание (состояние, размер, материал и т.п.):")


@router.message(AddListing.description)
async def add_listing_description(message: Message, state: FSMContext):
    description = message.text.strip()
    if len(description) > MAX_DESCRIPTION_LEN:
        await message.answer(
            f"Описание слишком длинное ({len(description)} символов). "
            f"Telegram ограничивает подпись к фото 1024 символами, поэтому описание "
            f"должно быть короче {MAX_DESCRIPTION_LEN} символов (с учётом названия и цены). "
            "Сократи и пришли заново."
        )
        return
    await state.update_data(description=description)
    await state.set_state(AddListing.brand)
    await message.answer(
        "Бренд (например: Uniqlo). Если хочешь привязать гайд по размерам — "
        "название должно совпадать с брендом гайда. Если бренда нет — отправь «-»."
    )


@router.message(AddListing.brand)
async def add_listing_brand(message: Message, state: FSMContext):
    brand = message.text.strip()
    await state.update_data(brand=None if brand == "-" else brand)
    await state.set_state(AddListing.photo)
    await message.answer("Пришли одно фото товара (просто фото, без файла-документа).")


@router.message(AddListing.photo, F.photo)
async def add_listing_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    photo_id = message.photo[-1].file_id
    listing_id = db.add_listing(
        title=data["title"],
        price=data["price"],
        description=data["description"],
        avito_url=data["avito_url"],
        brand=data.get("brand"),
        photo_id=photo_id,
    )
    await state.clear()
    await message.answer(f"✅ Товар #{listing_id} добавлен и уже виден в каталоге.")


@router.message(AddListing.photo)
async def add_listing_photo_invalid(message: Message):
    await message.answer("Нужно именно фото. Пришли картинку товара.")


# ===================== /edit: редактирование товара =====================

class EditListing(StatesGroup):
    waiting_value = State()


@router.message(Command("edit"))
async def edit_start(message: Message):
    if not is_admin(message.from_user.id):
        return
    listings = db.list_listings(active_only=False)
    if not listings:
        await message.answer("Пока нет ни одного товара. Добавь через /add")
        return
    await message.answer("Какой товар редактируем?", reply_markup=kb.edit_listings_kb(listings))


@router.callback_query(F.data.startswith("editsel:"))
async def edit_select_listing(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer()
        return
    listing_id = int(callback.data.split(":")[1])
    await callback.message.edit_text(
        "Что меняем в этом товаре?", reply_markup=kb.edit_fields_kb(listing_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("editfield:"))
async def edit_select_field(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer()
        return
    _, listing_id, field = callback.data.split(":")
    await state.set_state(EditListing.waiting_value)
    await state.update_data(listing_id=int(listing_id), field=field)

    if field == "photo_id":
        await callback.message.edit_text("Пришли новое фото товара.")
    else:
        label = kb.EDIT_FIELDS[field]
        await callback.message.edit_text(f"Пришли новое значение для «{label}»:")
    await callback.answer()


@router.message(EditListing.waiting_value, F.photo)
async def edit_apply_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    if data["field"] != "photo_id":
        await message.answer("Для этого поля нужен текст, а не фото.")
        return
    db.update_listing_field(data["listing_id"], "photo_id", message.photo[-1].file_id)
    await state.clear()
    await message.answer(f"✅ Товар #{data['listing_id']} обновлён.")


@router.message(EditListing.waiting_value, F.text)
async def edit_apply_text(message: Message, state: FSMContext):
    data = await state.get_data()
    if data["field"] == "photo_id":
        await message.answer("Для фото нужно прислать именно картинку.")
        return
    value = message.text.strip()
    if data["field"] == "description" and len(value) > MAX_DESCRIPTION_LEN:
        await message.answer(
            f"Описание слишком длинное ({len(value)} символов). "
            f"Должно быть короче {MAX_DESCRIPTION_LEN} символов. Сократи и пришли заново."
        )
        return
    db.update_listing_field(data["listing_id"], data["field"], value)
    await state.clear()
    await message.answer(f"✅ Товар #{data['listing_id']} обновлён.")


# ===================== FSM: добавление гайда по размерам =====================

class AddGuide(StatesGroup):
    brand = State()
    text = State()
    photo = State()


@router.message(Command("addguide"))
async def add_guide_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(AddGuide.brand)
    await message.answer("Название бренда для гайда (должно совпадать с брендом в товарах):")


@router.message(AddGuide.brand)
async def add_guide_brand(message: Message, state: FSMContext):
    await state.update_data(brand=message.text.strip())
    await state.set_state(AddGuide.text)
    await message.answer("Текст гайда (как подобрать размер для этого бренда):")


@router.message(AddGuide.text)
async def add_guide_text(message: Message, state: FSMContext):
    await state.update_data(text=message.text.strip())
    await state.set_state(AddGuide.photo)
    await message.answer("Пришли фото размерной таблицы, либо отправь /skip, если фото не нужно.")


@router.message(AddGuide.photo, Command("skip"))
async def add_guide_skip_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    guide_id = db.add_guide(data["brand"], data["text"], photo_id=None)
    await state.clear()
    await message.answer(f"✅ Гайд #{guide_id} для бренда «{data['brand']}» добавлен.")


@router.message(AddGuide.photo, F.photo)
async def add_guide_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    photo_id = message.photo[-1].file_id
    guide_id = db.add_guide(data["brand"], data["text"], photo_id=photo_id)
    await state.clear()
    await message.answer(f"✅ Гайд #{guide_id} для бренда «{data['brand']}» добавлен.")


# ===================== Админ: список и удаление товаров =====================

@router.message(Command("mylistings"))
async def my_listings(message: Message):
    if not is_admin(message.from_user.id):
        return
    listings = db.list_listings(active_only=False)
    if not listings:
        await message.answer("Пока нет ни одного товара. Добавь через /add")
        return
    await message.answer("Нажми, чтобы удалить товар:", reply_markup=kb.admin_listings_kb(listings))


@router.callback_query(F.data.startswith("del:"))
async def delete_listing_cb(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer()
        return
    listing_id = int(callback.data.split(":")[1])
    db.delete_listing(listing_id)
    await callback.answer("Удалено")
    await callback.message.edit_text("Товар удалён.")


# ===================== Покупатель: меню, каталог, гайды =====================

@router.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "Привет! Здесь можно посмотреть мои товары и подобрать размер перед покупкой 👇",
        reply_markup=kb.main_menu_kb(),
    )


@router.callback_query(F.data == "menu")
async def back_to_menu(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer("Главное меню:", reply_markup=kb.main_menu_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("catalog:"))
async def show_catalog(callback: CallbackQuery):
    listings = db.list_listings(active_only=True)
    if not listings:
        await callback.message.edit_text(
            "Каталог пока пуст.", reply_markup=kb.back_to_menu_kb()
        )
        await callback.answer()
        return

    index = int(callback.data.split(":")[1])
    index = max(0, min(index, len(listings) - 1))
    item = listings[index]

    caption = f"<b>{item['title']}</b>\n💰 {item['price']}\n\n{item['description']}"
    if len(caption) > 1024:
        caption = caption[:1020] + "…"
    markup = kb.catalog_item_kb(item, index, len(listings))

    try:
        await callback.message.delete()
        if item["photo_id"]:
            await callback.message.answer_photo(
                item["photo_id"], caption=caption, reply_markup=markup, parse_mode="HTML"
            )
        else:
            await callback.message.answer(caption, reply_markup=markup, parse_mode="HTML")
    except Exception:
        logging.exception("Не удалось показать товар #%s в каталоге", item["id"])
        await callback.message.answer(
            "Не получилось показать этот товар (слишком длинное описание или ошибка). "
            "Сообщи об этом администратору.",
            reply_markup=kb.back_to_menu_kb(),
        )
    finally:
        await callback.answer()


@router.callback_query(F.data == "guides")
async def show_guides_list(callback: CallbackQuery):
    guides = db.list_guides()
    if not guides:
        await callback.message.edit_text(
            "Гайдов пока нет.", reply_markup=kb.back_to_menu_kb()
        )
        await callback.answer()
        return
    await callback.message.edit_text(
        "Выбери бренд, чтобы посмотреть, как подобрать размер:",
        reply_markup=kb.guides_list_kb(guides),
    )
    await callback.answer()


async def _send_guide(callback: CallbackQuery, guide):
    await callback.message.delete()
    if guide["photo_id"]:
        await callback.message.answer_photo(
            guide["photo_id"], caption=guide["text"], reply_markup=kb.back_to_menu_kb()
        )
    else:
        await callback.message.answer(guide["text"], reply_markup=kb.back_to_menu_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("guide:"))
async def show_guide(callback: CallbackQuery):
    guide_id = int(callback.data.split(":")[1])
    with db.get_conn() as conn:
        guide = conn.execute("SELECT * FROM guides WHERE id = ?", (guide_id,)).fetchone()
    if not guide:
        await callback.answer("Гайд не найден", show_alert=True)
        return
    await _send_guide(callback, guide)


@router.callback_query(F.data.startswith("guide_for:"))
async def show_guide_for_brand(callback: CallbackQuery):
    brand = callback.data.split(":", 1)[1]
    guide = db.get_guide_by_brand(brand)
    if not guide:
        await callback.answer("Для этого бренда гайда пока нет", show_alert=True)
        return
    await _send_guide(callback, guide)


@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery):
    await callback.answer()


async def main():
    if not config.BOT_TOKEN:
        raise RuntimeError("Не задан BOT_TOKEN. См. README.md")

    db.init_db()
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())