import asyncio
import logging
import os
import time

from aiogram import BaseMiddleware, Bot, Dispatcher, Router, F
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


async def _callback_error(callback: CallbackQuery, text: str = "Что-то пошло не так, попробуй ещё раз."):
    logging.warning("Некорректные данные в callback: %r", callback.data)
    try:
        await callback.answer(text, show_alert=True)
    except Exception:
        pass


class ThrottlingMiddleware(BaseMiddleware):
    """Не даёт одному пользователю слать действия чаще, чем раз в RATE_LIMIT секунд."""

    RATE_LIMIT = 0.4  # секунд между действиями одного пользователя

    def __init__(self):
        self._last_action: dict[int, float] = {}

    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        if user is not None:
            now = time.monotonic()
            last = self._last_action.get(user.id, 0.0)
            if now - last < self.RATE_LIMIT:
                if isinstance(event, CallbackQuery):
                    try:
                        await event.answer()
                    except Exception:
                        pass
                return None
            self._last_action[user.id] = now
        return await handler(event, data)


# ===================== FSM: добавление товара =====================

class AddListing(StatesGroup):
    url = State()
    title = State()
    price = State()
    description = State()
    brand = State()
    category = State()
    size = State()
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
    await state.set_state(AddListing.category)
    await message.answer(
        "Категория (например: Куртки, Кроссовки, Футболки). Используй одно и то же "
        "название для одинаковых товаров — тогда они будут попадать в одну кнопку "
        "у покупателя. Если без категории — отправь «-»."
    )


@router.message(AddListing.category)
async def add_listing_category(message: Message, state: FSMContext):
    category = message.text.strip()
    await state.update_data(category=None if category == "-" else category)
    await state.set_state(AddListing.size)
    await message.answer(
        "Размер (например: XL или 42). Если без размера — отправь «-»."
    )


@router.message(AddListing.size)
async def add_listing_size(message: Message, state: FSMContext):
    size = message.text.strip()
    await state.update_data(size=None if size == "-" else size)
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
        category=data.get("category"),
        size=data.get("size"),
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
    try:
        listing_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await _callback_error(callback)
        return
    await callback.message.edit_text(
        "Что меняем в этом товаре?", reply_markup=kb.edit_fields_kb(listing_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("editfield:"))
async def edit_select_field(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer()
        return
    try:
        _, listing_id_str, field = callback.data.split(":")
        listing_id = int(listing_id_str)
        if field != "photo_id":
            label = kb.EDIT_FIELDS[field]
    except (ValueError, KeyError):
        await _callback_error(callback)
        return

    await state.set_state(EditListing.waiting_value)
    await state.update_data(listing_id=listing_id, field=field)

    if field == "photo_id":
        await callback.message.edit_text("Пришли новое фото товара.")
    else:
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
    try:
        listing_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await _callback_error(callback)
        return
    db.delete_listing(listing_id)
    await callback.answer("Удалено")
    await callback.message.edit_text("Товар удалён.")


# ===================== Покупатель: меню, каталог, гайды =====================

class Browse(StatesGroup):
    categories = State()
    sizes = State()
    guides = State()


@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Привет! Здесь можно посмотреть мои товары и подобрать размер перед покупкой 👇",
        reply_markup=kb.main_reply_kb(),
    )


@router.message(F.text == "⬅️ Главное меню")
async def menu_button(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню:", reply_markup=kb.main_reply_kb())


@router.callback_query(F.data == "menu")
async def back_to_menu_inline(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer("Главное меню:", reply_markup=kb.main_reply_kb())
    await callback.answer()


async def _send_catalog_item(target, listings, index: int):
    """target — это Message (новое сообщение) либо CallbackQuery (пагинация)."""
    is_callback = isinstance(target, CallbackQuery)
    message = target.message if is_callback else target

    if not listings:
        await message.answer("Каталог пока пуст.")
        if is_callback:
            await target.answer()
        return

    index = max(0, min(index, len(listings) - 1))
    item = listings[index]

    caption = f"<b>{item['title']}</b>\n💰 {item['price']}\n\n{item['description']}"
    if len(caption) > 1024:
        caption = caption[:1020] + "…"
    markup = kb.catalog_item_kb(item, index, len(listings))

    try:
        if is_callback:
            await message.delete()
        if item["photo_id"]:
            await message.answer_photo(item["photo_id"], caption=caption, reply_markup=markup, parse_mode="HTML")
        else:
            await message.answer(caption, reply_markup=markup, parse_mode="HTML")
    except Exception:
        logging.exception("Не удалось показать товар #%s в каталоге", item["id"])
        await message.answer("Не получилось показать этот товар. Сообщи об этом администратору.")
    finally:
        if is_callback:
            await target.answer()


@router.message(F.text == "📦 Каталог")
async def menu_catalog(message: Message, state: FSMContext):
    await state.clear()
    listings = db.list_listings(active_only=True)
    await _send_catalog_item(message, listings, 0)


@router.callback_query(F.data.startswith("catalog:"))
async def paginate_catalog(callback: CallbackQuery):
    try:
        index = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await _callback_error(callback)
        return
    listings = db.list_listings(active_only=True)
    await _send_catalog_item(callback, listings, index)


@router.message(F.text == "🗂 По категориям")
async def menu_categories(message: Message, state: FSMContext):
    categories = db.list_categories(active_only=True)
    if not categories:
        await message.answer("Категорий пока нет.", reply_markup=kb.main_reply_kb())
        await state.clear()
        return
    await state.set_state(Browse.categories)
    await message.answer("Выбери категорию:", reply_markup=kb.categories_reply_kb(categories))


@router.message(Browse.categories)
async def choose_category(message: Message, state: FSMContext):
    category = message.text.strip()
    categories = db.list_categories(active_only=True)
    if category not in categories:
        await message.answer("Выбери категорию кнопкой ниже 👇")
        return
    await state.update_data(browse_category=category, browse_size=None)
    await state.set_state(Browse.sizes)
    sizes = db.list_sizes_in_category(category, active_only=True)
    await message.answer(
        f"Категория «{category}». Выбери размер:",
        reply_markup=kb.sizes_reply_kb(sizes),
    )


@router.message(F.text == "⬅️ Назад", Browse.sizes)
async def sizes_back_to_categories(message: Message, state: FSMContext):
    categories = db.list_categories(active_only=True)
    await state.set_state(Browse.categories)
    await message.answer("Выбери категорию:", reply_markup=kb.categories_reply_kb(categories))


async def _send_filtered_item(target, state: FSMContext, index: int):
    is_callback = isinstance(target, CallbackQuery)
    message = target.message if is_callback else target

    data = await state.get_data()
    category = data.get("browse_category")
    size = data.get("browse_size")
    listings = db.list_listings_filtered(category=category, size=size, active_only=True)

    if not listings:
        await message.answer("По этому фильтру пока ничего нет.")
        if is_callback:
            await target.answer()
        return

    index = max(0, min(index, len(listings) - 1))
    item = listings[index]

    caption = f"<b>{item['title']}</b>\n💰 {item['price']}\n\n{item['description']}"
    if len(caption) > 1024:
        caption = caption[:1020] + "…"
    markup = kb.filtered_item_kb(item, index, len(listings))

    try:
        if is_callback:
            await message.delete()
        if item["photo_id"]:
            await message.answer_photo(item["photo_id"], caption=caption, reply_markup=markup, parse_mode="HTML")
        else:
            await message.answer(caption, reply_markup=markup, parse_mode="HTML")
    except Exception:
        logging.exception("Не удалось показать товар #%s по фильтру", item["id"])
        await message.answer("Не получилось показать этот товар. Сообщи об этом администратору.")
    finally:
        if is_callback:
            await target.answer()


@router.message(Browse.sizes)
async def choose_size(message: Message, state: FSMContext):
    value = message.text.strip()
    data = await state.get_data()
    category = data.get("browse_category")
    sizes = db.list_sizes_in_category(category, active_only=True) if category else []
    if value != "Все размеры" and value not in sizes:
        await message.answer("Выбери размер кнопкой ниже 👇")
        return
    await state.update_data(browse_size=None if value == "Все размеры" else value)
    await _send_filtered_item(message, state, 0)


@router.callback_query(F.data.startswith("catpage:"))
async def paginate_filtered(callback: CallbackQuery, state: FSMContext):
    try:
        index = int(callback.data.split(":", 1)[1])
    except (IndexError, ValueError):
        await _callback_error(callback)
        return
    await _send_filtered_item(callback, state, index)


@router.callback_query(F.data == "backsizes")
async def back_to_sizes_from_item(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    category = data.get("browse_category")
    try:
        await callback.message.delete()
    except Exception:
        pass
    if not category:
        await state.clear()
        await callback.message.answer("Главное меню:", reply_markup=kb.main_reply_kb())
        await callback.answer()
        return
    await state.set_state(Browse.sizes)
    sizes = db.list_sizes_in_category(category, active_only=True)
    await callback.message.answer(
        f"Категория «{category}». Выбери размер:",
        reply_markup=kb.sizes_reply_kb(sizes),
    )
    await callback.answer()


@router.message(F.text == "📏 Гайды по размерам")
async def menu_guides(message: Message, state: FSMContext):
    guides = db.list_guides()
    if not guides:
        await message.answer("Гайдов пока нет.", reply_markup=kb.main_reply_kb())
        await state.clear()
        return
    await state.set_state(Browse.guides)
    await message.answer(
        "Выбери бренд, чтобы посмотреть, как подобрать размер:",
        reply_markup=kb.guides_reply_kb(guides),
    )


@router.message(Browse.guides)
async def choose_guide(message: Message, state: FSMContext):
    brand = message.text.strip()
    guide = db.get_guide_by_brand(brand)
    if not guide:
        await message.answer("Выбери бренд кнопкой ниже 👇")
        return
    if guide["photo_id"]:
        await message.answer_photo(guide["photo_id"], caption=guide["text"])
    else:
        await message.answer(guide["text"])


@router.callback_query(F.data.startswith("guide_for:"))
async def show_guide_for_brand(callback: CallbackQuery):
    brand = callback.data.split(":", 1)[1]
    guide = db.get_guide_by_brand(brand)
    if not guide:
        await callback.answer("Для этого бренда гайда пока нет", show_alert=True)
        return
    if guide["photo_id"]:
        await callback.message.answer_photo(guide["photo_id"], caption=guide["text"])
    else:
        await callback.message.answer(guide["text"])
    await callback.answer()


@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery):
    await callback.answer()


async def main():
    if not config.BOT_TOKEN:
        raise RuntimeError("Не задан BOT_TOKEN. См. README.md")

    logging.info(
        "DB_PATH=%s | DATA_DIR env=%r | SHARED_DIR env=%r | существует ли база до старта: %s",
        config.DB_PATH,
        os.getenv("DATA_DIR"),
        os.getenv("SHARED_DIR"),
        os.path.exists(config.DB_PATH),
    )

    db.init_db()
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()
    throttling = ThrottlingMiddleware()
    dp.message.middleware(throttling)
    dp.callback_query.middleware(throttling)
    dp.include_router(router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())