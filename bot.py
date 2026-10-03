import asyncio
import os
from datetime import datetime
from html import escape

import pytz
from aiohttp import web

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)


# =========================================================
# ENVIRONMENT VARIABLES
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")
PORT = int(os.getenv("PORT", "10000"))

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable kiritilmagan!")


# =========================================================
# BOT
# =========================================================

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    ),
)

dp = Dispatcher(storage=MemoryStorage())


# =========================================================
# STATES
# =========================================================

class Order(StatesGroup):
    name = State()
    phone = State()
    address = State()

    item_type = State()
    width = State()
    length = State()
    korpacha_length = State()

    bed_type = State()
    quantity = State()
    weight = State()

    service = State()
    price = State()


# =========================================================
# KEYBOARDS
# =========================================================

def type_buttons():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📌 Gilam",
                    callback_data="type_gilam"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🛋 Ko‘rpacha",
                    callback_data="type_korpacha"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🛏 To‘shak",
                    callback_data="type_toshak"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🛏 Adyol / Par ko‘rpa",
                    callback_data="type_adyol"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🪟 Parda",
                    callback_data="type_parda"
                )
            ],
        ]
    )


def bed_type_buttons():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="1 kishilik",
                    callback_data="bed_1kishilik"
                )
            ],
            [
                InlineKeyboardButton(
                    text="2 kishilik",
                    callback_data="bed_2kishilik"
                )
            ],
        ]
    )


def item_buttons():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Yana buyum qo‘shish",
                    callback_data="add_item"
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ Buyurtmani yakunlash",
                    callback_data="finish"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Bekor qilish",
                    callback_data="cancel"
                )
            ],
        ]
    )


def group_receipt_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚚 Yetkazib berildi",
                    callback_data="mark_delivered"
                )
            ]
        ]
    )


# =========================================================
# HELPERS
# =========================================================

def money(value):
    return f"{value:,.0f}".replace(",", " ")


def make_receipt(
    data,
    status="⏳ YETKAZILISHI KERAK",
    delivered_by=None,
    delivered_time=None,
):
    items = data.get("items", [])

    lines = [
        "🧾 <b>SOF LUX</b>",
        "<b>MAHSULOT QABUL QILISH DALOLATNOMASI</b>",
        f"<b>Holati:</b> {status}",
    ]

    if delivered_by:
        lines.append(
            f"<b>Topshirdi:</b> "
            f"{escape(delivered_by)} ({delivered_time})"
        )

    lines.extend(
        [
            "",
            f"👤 Mijoz: {escape(data.get('name', ''))}",
            f"📞 Telefon: {escape(data.get('phone', ''))}",
            f"📍 Manzil: {escape(data.get('address', ''))}",
            "",
            "━━━━━━━━━━━━━━━━━━",
        ]
    )

    total_price = 0

    for i, item in enumerate(items, start=1):
        total = item["total"]
        total_price += total

        lines.append(
            f"<b>{i}. {escape(item['type'])}</b>"
        )

        if item["category"] == "gilam":
            lines.append(
                f"📐 O‘lchami: "
                f"{item['width']:g} × "
                f"{item['length']:g} m "
                f"({item['area']:.2f} m²)"
            )

            lines.append(
                f"💵 1 m²: {money(item['price'])} so‘m"
            )

        elif item["category"] == "korpacha":
            lines.append(
                f"📏 Uzunligi: {item['length']:g} m"
            )

            lines.append(
                f"💵 1 m: {money(item['price'])} so‘m"
            )

        elif item["category"] in ["toshak", "adyol"]:
            lines.append(
                f"🏷 Turi: {escape(item['sub_type'])}"
            )

            lines.append(
                f"📦 Soni: {item['quantity']} dona"
            )

            lines.append(
                f"💵 1 dona: {money(item['price'])} so‘m"
            )

        elif item["category"] == "parda":
            lines.append(
                f"⚖️ Og‘irligi: {item['weight']:g} kg"
            )

            lines.append(
                f"💵 1 kg: {money(item['price'])} so‘m"
            )

        lines.extend(
            [
                f"🧼 Xizmat: {escape(item['service'])}",
                f"💰 Jami: {money(total)} so‘m",
                "",
            ]
        )

    lines.extend(
        [
            "━━━━━━━━━━━━━━━━━━",
            f"📦 Buyumlar soni: {len(items)} ta",
            f"💰 <b>UMUMIY SUMMA: "
            f"{money(total_price)} so‘m</b>",
            "",
            "SOF LUX — Gilam va matolar yuvish markazi",
        ]
    )

    return "\n".join(lines)


# =========================================================
# START
# =========================================================

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()

    await state.update_data(
        items=[]
    )

    await message.answer(
        "🧾 <b>SOF LUX</b>\n"
        "Qabul qilish dalolatnomasi\n\n"
        "Mijozning ism-familiyasini kiriting:"
    )

    await state.set_state(Order.name)


# =========================================================
# CANCEL COMMAND
# =========================================================

@dp.message(Command("cancel"))
async def cancel(
    message: Message,
    state: FSMContext
):
    await state.clear()

    await message.answer(
        "❌ Buyurtma bekor qilindi.\n"
        "Yangi buyurtma uchun /start bosing."
    )


# =========================================================
# CUSTOMER NAME
# =========================================================

@dp.message(Order.name)
async def get_name(
    message: Message,
    state: FSMContext
):
    text = (message.text or "").strip()

    if not text:
        await message.answer(
            "❌ Ism-familiya bo‘sh bo‘lmasligi kerak."
        )
        return

    await state.update_data(
        name=text
    )

    await message.answer(
        "📞 Mijoz telefon raqamini kiriting:"
    )

    await state.set_state(Order.phone)


# =========================================================
# PHONE
# =========================================================

@dp.message(Order.phone)
async def get_phone(
    message: Message,
    state: FSMContext
):
    text = (message.text or "").strip()

    if not text:
        await message.answer(
            "❌ Telefon raqamini kiriting."
        )
        return

    await state.update_data(
        phone=text
    )

    await message.answer(
        "📍 Mijoz manzilini kiriting:"
    )

    await state.set_state(Order.address)


# =========================================================
# ADDRESS
# =========================================================

@dp.message(Order.address)
async def get_address(
    message: Message,
    state: FSMContext
):
    text = (message.text or "").strip()

    if not text:
        await message.answer(
            "❌ Manzil bo‘sh bo‘lmasligi kerak."
        )
        return

    await state.update_data(
        address=text
    )

    await message.answer(
        "Mahsulot turini tanlang:",
        reply_markup=type_buttons()
    )


# =========================================================
# PRODUCT TYPE
# =========================================================

@dp.callback_query(F.data.startswith("type_"))
async def process_type(
    callback: CallbackQuery,
    state: FSMContext
):
    await callback.answer()

    category = callback.data.split("_", 1)[1]

    await state.update_data(
        current_category=category
    )

    if category == "gilam":

        await state.update_data(
            current_type="Gilam"
        )

        await callback.message.answer(
            "Gilamning ENIni metrda kiriting:\n"
            "Masalan: 3.5"
        )

        await state.set_state(Order.width)

    elif category == "korpacha":

        await state.update_data(
            current_type="Ko‘rpacha"
        )

        await callback.message.answer(
            "Ko‘rpacha UZUNLIGINI metrda kiriting:\n"
            "Masalan: 3.8"
        )

        await state.set_state(
            Order.korpacha_length
        )

    elif category in ["toshak", "adyol"]:

        title = (
            "To‘shak"
            if category == "toshak"
            else "Adyol / Par ko‘rpa"
        )

        await state.update_data(
            current_type=title
        )

        await callback.message.answer(
            f"{title} turini tanlang:",
            reply_markup=bed_type_buttons()
        )

    elif category == "parda":

        await state.update_data(
            current_type="Parda"
        )

        await callback.message.answer(
            "Pardaning OG‘IRLIGINI (kg) kiriting:\n"
            "Masalan: 4.5"
        )

        await state.set_state(Order.weight)


# =========================================================
# CARPET WIDTH
# =========================================================

@dp.message(Order.width)
async def get_width(
    message: Message,
    state: FSMContext
):
    try:
        width = float(
            (message.text or "")
            .replace(",", ".")
            .strip()
        )

        if width <= 0:
            raise ValueError

    except ValueError:
        await message.answer(
            "❌ Enini to‘g‘ri kiriting.\n"
            "Masalan: 3.5"
        )
        return

    await state.update_data(
        current_width=width
    )

    await message.answer(
        "Gilamning BO‘YIni metrda kiriting:\n"
        "Masalan: 4"
    )

    await state.set_state(Order.length)


# =========================================================
# CARPET LENGTH
# =========================================================

@dp.message(Order.length)
async def get_length(
    message: Message,
    state: FSMContext
):
    try:
        length = float(
            (message.text or "")
            .replace(",", ".")
            .strip()
        )

        if length <= 0:
            raise ValueError

    except ValueError:
        await message.answer(
            "❌ Bo‘yini to‘g‘ri kiriting.\n"
            "Masalan: 4"
        )
        return

    await state.update_data(
        current_length=length
    )

    await message.answer(
        "Xizmat turini kiriting:\n"
        "Masalan: Oddiy yuvish, dog‘ ketkazish"
    )

    await state.set_state(Order.service)


# =========================================================
# KORPACHA LENGTH
# =========================================================

@dp.message(Order.korpacha_length)
async def get_korpacha_length(
    message: Message,
    state: FSMContext
):
    try:
        length = float(
            (message.text or "")
            .replace(",", ".")
            .strip()
        )

        if length <= 0:
            raise ValueError

    except ValueError:
        await message.answer(
            "❌ Uzunlikni to‘g‘ri kiriting.\n"
            "Masalan: 3.5"
        )
        return

    await state.update_data(
        current_length=length
    )

    await message.answer(
        "Xizmat turini kiriting:\n"
        "Masalan: Oddiy yuvish, tozalash"
    )

    await state.set_state(Order.service)


# =========================================================
# BED TYPE
# =========================================================

@dp.callback_query(F.data.startswith("bed_"))
async def process_bed_type(
    callback: CallbackQuery,
    state: FSMContext
):
    await callback.answer()

    bed_type = (
        "1 kishilik"
        if callback.data == "bed_1kishilik"
        else "2 kishilik"
    )

    await state.update_data(
        current_sub_type=bed_type
    )

    await callback.message.answer(
        "Soni (nechta) ekanligini kiriting:"
    )

    await state.set_state(Order.quantity)


# =========================================================
# QUANTITY
# =========================================================

@dp.message(Order.quantity)
async def get_quantity(
    message: Message,
    state: FSMContext
):
    try:
        qty = int(
            (message.text or "").strip()
        )

        if qty <= 0:
            raise ValueError

    except ValueError:
        await message.answer(
            "❌ Raqam bilan kiriting.\n"
            "Masalan: 2"
        )
        return

    await state.update_data(
        current_quantity=qty
    )

    await message.answer(
        "Xizmat turini kiriting:\n"
        "Masalan: Oddiy yuvish"
    )

    await state.set_state(Order.service)


# =========================================================
# CURTAIN WEIGHT
# =========================================================

@dp.message(Order.weight)
async def get_weight(
    message: Message,
    state: FSMContext
):
    try:
        weight = float(
            (message.text or "")
            .replace(",", ".")
            .strip()
        )

        if weight <= 0:
            raise ValueError

    except ValueError:
        await message.answer(
            "❌ Og‘irlikni to‘g‘ri kiriting.\n"
            "Masalan: 4.5"
        )
        return

    await state.update_data(
        current_weight=weight
    )

    await message.answer(
        "Xizmat turini kiriting:\n"
        "Masalan: Kimyoviy tozalash"
    )

    await state.set_state(Order.service)


# =========================================================
# SERVICE
# =========================================================

@dp.message(Order.service)
async def get_service(
    message: Message,
    state: FSMContext
):
    service = (message.text or "").strip()

    if not service:
        await message.answer(
            "❌ Xizmat turini kiriting."
        )
        return

    await state.update_data(
        current_service=service
    )

    data = await state.get_data()

    cat = data.get("current_category")

    if cat == "gilam":
        unit = "1 m²"

    elif cat == "korpacha":
        unit = "1 metr"

    elif cat in ["toshak", "adyol"]:
        unit = (
            f"1 dona "
            f"({data.get('current_sub_type', '')})"
        )

    elif cat == "parda":
        unit = "1 kg"

    else:
        unit = "1 dona"

    await message.answer(
        f"{unit} uchun narxni so‘mda kiriting:\n"
        "Masalan: 15000"
    )

    await state.set_state(Order.price)


# =========================================================
# PRICE
# =========================================================

@dp.message(Order.price)
async def get_price(
    message: Message,
    state: FSMContext
):
    clean_text = (
        (message.text or "")
        .replace(" ", "")
        .replace(",", ".")
        .strip()
    )

    try:
        price = float(clean_text)

        if price <= 0:
            raise ValueError

    except ValueError:
        await message.answer(
            "❌ Narxni raqamlarda kiriting.\n"
            "Masalan: 15000"
        )
        return

    data = await state.get_data()

    cat = data.get("current_category")

    if not cat:
        await message.answer(
            "❌ Xatolik yuz berdi.\n"
            "Iltimos, /start bosing."
        )

        await state.clear()
        return

    item = {
        "category": cat,
        "type": data.get(
            "current_type",
            "Buyum"
        ),
        "service": data.get(
            "current_service",
            "Tozalash"
        ),
        "price": price,
    }

    # -------------------------
    # GILAM
    # -------------------------

    if cat == "gilam":

        width = data.get(
            "current_width",
            0
        )

        length = data.get(
            "current_length",
            0
        )

        area = width * length

        item["width"] = width
        item["length"] = length
        item["area"] = area
        item["total"] = area * price

    # -------------------------
    # KORPACHA
    # -------------------------

    elif cat == "korpacha":

        length = data.get(
            "current_length",
            0
        )

        item["length"] = length
        item["total"] = length * price

    # -------------------------
    # TOSHAK / ADYOL
    # -------------------------

    elif cat in ["toshak", "adyol"]:

        item["sub_type"] = data.get(
            "current_sub_type",
            ""
        )

        quantity = data.get(
            "current_quantity",
            1
        )

        item["quantity"] = quantity
        item["total"] = quantity * price

    # -------------------------
    # PARDA
    # -------------------------

    elif cat == "parda":

        weight = data.get(
            "current_weight",
            0
        )

        item["weight"] = weight
        item["total"] = weight * price

    else:

        item["total"] = price

    # =====================================================
    # ITEMS
    # =====================================================

    items = data.get("items", [])

    if not isinstance(items, list):
        items = []

    items.append(item)

    await state.update_data(
        items=items
    )

    await message.answer(
        f"✅ <b>{escape(item['type'])} "
        f"qo‘shildi!</b>\n"
        f"💰 Summa: "
        f"{money(item['total'])} so‘m\n\n"
        "Yana buyum qo‘shasizmi yoki "
        "buyurtmani yakunlaysizmi?",
        reply_markup=item_buttons()
    )


# =========================================================
# ADD ITEM
# =========================================================

@dp.callback_query(F.data == "add_item")
async def add_item(
    callback: CallbackQuery,
    state: FSMContext
):
    await callback.answer()

    await callback.message.answer(
        "Mahsulot turini tanlang:",
        reply_markup=type_buttons()
    )


# =========================================================
# FINISH ORDER
# =========================================================

@dp.callback_query(F.data == "finish")
async def finish(
    callback: CallbackQuery,
    state: FSMContext
):
    await callback.answer()

    data = await state.get_data()

    items = data.get(
        "items",
        []
    )

    if not items:
        await callback.message.answer(
            "❌ Buyurtmada hech qanday "
            "buyum yo‘q."
        )
        return

    receipt = make_receipt(data)

    # Mijozga chek
    await callback.message.answer(
        receipt
    )

    # Guruhga yuborish
    if GROUP_ID:

        try:
            group_id = int(
                str(GROUP_ID).strip()
            )

            await bot.send_message(
                chat_id=group_id,
                text=receipt,
                reply_markup=group_receipt_keyboard()
            )

        except ValueError:

            print(
                "❌ GROUP_ID noto‘g‘ri: "
                f"{GROUP_ID}"
            )

        except Exception as e:

            print(
                "❌ Guruhga yuborishda xatolik:",
                repr(e)
            )

    await state.clear()

    await callback.message.answer(
        "✅ Buyurtma qabul qilindi.\n\n"
        "Yangi buyurtma uchun "
        "/start bosing."
    )


# =========================================================
# CANCEL BUTTON
# =========================================================

@dp.callback_query(F.data == "cancel")
async def cancel_callback(
    callback: CallbackQuery,
    state: FSMContext
):
    await callback.answer()

    await state.clear()

    await callback.message.answer(
        "❌ Buyurtma bekor qilindi.\n"
        "Yangi buyurtma uchun /start bosing."
    )


# =========================================================
# DELIVERY
# =========================================================

@dp.callback_query(F.data == "mark_delivered")
async def process_delivery(
    callback: CallbackQuery
):
    user_name = callback.from_user.full_name

    tz = pytz.timezone(
        "Asia/Tashkent"
    )

    now_str = datetime.now(tz).strftime(
        "%d.%m.%Y %H:%M"
    )

    original_text = (
        callback.message.text
        or callback.message.caption
        or ""
    )

    if "✅ YETKAZILDI" in original_text:

        await callback.answer(
            "Bu buyurtma allaqachon "
            "yetkazilgan deb belgilangan!",
            show_alert=True
        )

        return

    updated_text = original_text.replace(
        "Holati:</b> ⏳ YETKAZILISHI KERAK",
        (
            "Holati:</b> ✅ YETKAZILDI\n"
            f"<b>Topshirdi:</b> "
            f"{escape(user_name)} "
            f"({now_str})"
        )
    )

    try:

        await callback.message.edit_text(
            text=updated_text,
            reply_markup=None,
            parse_mode=ParseMode.HTML
        )

        await callback.answer(
            "Buyurtma yetkazildi deb "
            "belgilandi!"
        )

    except Exception as e:

        print(
            "Delivery update xatosi:",
            repr(e)
        )

        await callback.answer(
            "❌ Buyurtma holatini "
            "o‘zgartirib bo‘lmadi.",
            show_alert=True
        )


# =========================================================
# RENDER WEB SERVER
# =========================================================

async def handle_ping(request):
    return web.Response(
        text="SOF LUX Bot is running OK!",
        status=200
    )


async def start_web_server():
    app = web.Application()

    app.router.add_get(
        "/",
        handle_ping
    )

    app.router.add_get(
        "/ping",
        handle_ping
    )

    runner = web.AppRunner(app)

    await runner.setup()

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        PORT
    )

    await site.start()

    print(
        f"🌐 Web server {PORT}-portda "
        "ishga tushdi."
    )


# =========================================================
# MAIN
# =========================================================

async def main():

    print(
        "🚀 SOF LUX bot ishga tushmoqda..."
    )

    print(
        f"🌐 PORT: {PORT}"
    )

    if GROUP_ID:
        print(
            f"👥 GROUP_ID: {GROUP_ID}"
        )
    else:
        print(
            "⚠️ GROUP_ID berilmagan. "
            "Buyurtmalar guruhga yuborilmaydi."
        )

    await asyncio.gather(
        start_web_server(),
        dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types()
        ),
    )


# =========================================================
# START APPLICATION
# =========================================================

if __name__ == "__main__":
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        print(
            "🛑 Bot to‘xtatildi."
        )
