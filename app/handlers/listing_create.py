from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from app.states.states import ListingCreate
from app.keyboards.user_kb import (
    cancel_kb, ranks_kb, links_kb, media_done_kb, preview_kb,
    preview_edit_kb, confirm_kb
)
from app.utils.formatters import format_listing_preview
from app.utils.validators import parse_positive_int, validate_media_combo
from app.utils.security import safe_edit, safe_answer
from app.services.listing_service import listing_service
from app.services.settings_service import settings_service
from app.services.balance_service import balance_service
from app.config import RANK_OPTIONS
from app.database.db import async_session
from app.database.repository import UserRepo

router = Router(name="listing_create")


def _empty_draft() -> dict:
    return {
        "current_rank": None,
        "peak_rank": None,
        "hero_count": None,
        "skin_count": None,
        "account_links": [],
        "media": [],  # list of (type, file_id)
        "price": None,
        "description": None,
    }


@router.message(F.text == "➕ E'LON BERISH")
async def start_create(msg: Message, state: FSMContext):
    await state.set_state(ListingCreate.current_rank)
    await state.update_data(draft=_empty_draft())
    await msg.answer(
        "1️⃣ <b>Hozirgi rank</b>ni tanlang:",
        reply_markup=ranks_kb("cr")
    )


@router.callback_query(F.data.startswith("cr:"), StateFilter(ListingCreate.current_rank))
async def set_current_rank(cb: CallbackQuery, state: FSMContext):
    rank = cb.data.split(":", 1)[1]
    data = await state.get_data()
    draft = data["draft"]
    draft["current_rank"] = rank
    await state.update_data(draft=draft)
    await state.set_state(ListingCreate.peak_rank)
    await safe_edit(cb, "2️⃣ <b>Eng yuqori (peak) rank</b>ni tanlang:",
                    reply_markup=ranks_kb("pr"))
    await safe_answer(cb)


@router.callback_query(F.data.startswith("pr:"), StateFilter(ListingCreate.peak_rank))
async def set_peak_rank(cb: CallbackQuery, state: FSMContext):
    rank = cb.data.split(":", 1)[1]
    data = await state.get_data()
    draft = data["draft"]
    draft["peak_rank"] = rank
    await state.update_data(draft=draft)
    await state.set_state(ListingCreate.hero_count)
    await safe_edit(cb, "3️⃣ <b>Hero soni</b>ni kiriting (masalan: 87):", reply_markup=cancel_kb())
    await safe_answer(cb)


@router.message(StateFilter(ListingCreate.hero_count), F.text)
async def set_hero(msg: Message, state: FSMContext):
    v = parse_positive_int(msg.text, min_v=1, max_v=10000)
    if v is None:
        await msg.answer("❌ Iltimos, to'g'ri musbat son kiriting.")
        return
    data = await state.get_data()
    data["draft"]["hero_count"] = v
    await state.update_data(draft=data["draft"])
    await state.set_state(ListingCreate.skin_count)
    await msg.answer("4️⃣ <b>Skin soni</b>ni kiriting (masalan: 143):", reply_markup=cancel_kb())


@router.message(StateFilter(ListingCreate.skin_count), F.text)
async def set_skin(msg: Message, state: FSMContext):
    v = parse_positive_int(msg.text, min_v=1, max_v=10000)
    if v is None:
        await msg.answer("❌ Iltimos, to'g'ri musbat son kiriting.")
        return
    data = await state.get_data()
    data["draft"]["skin_count"] = v
    await state.update_data(draft=data["draft"])
    await state.set_state(ListingCreate.account_links)
    await msg.answer(
        "5️⃣ Akkauntda <b>bog'langan</b> xizmatlarni belgilang:",
        reply_markup=links_kb([])
    )


@router.callback_query(F.data.startswith("link_toggle:"), StateFilter(ListingCreate.account_links))
async def toggle_link(cb: CallbackQuery, state: FSMContext):
    name = cb.data.split(":", 1)[1]
    data = await state.get_data()
    links = data["draft"]["account_links"]
    if name in links:
        links.remove(name)
    else:
        links.append(name)
    data["draft"]["account_links"] = links
    await state.update_data(draft=data["draft"])
    await safe_edit(cb, "5️⃣ Akkauntda <b>bog'langan</b> xizmatlarni belgilang:",
                    reply_markup=links_kb(links))
    await safe_answer(cb)


@router.callback_query(F.data == "links_done", StateFilter(ListingCreate.account_links))
async def links_done(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data["draft"]["account_links"]:
        await safe_answer(cb, "Kamida bitta link tanlang", show_alert=True)
        return
    await state.set_state(ListingCreate.media)
    await state.update_data(draft=data["draft"])
    await safe_edit(
        cb,
        "6️⃣ <b>Media</b> yuboring:\n"
        "• 1 tagacha rasm\n"
        "• 2 tagacha rasm\n"
        "• 1 ta video\n\n"
        "Rasmlarni rasm sifatida yuboring.",
        reply_markup=media_done_kb()
    )
    await safe_answer(cb)


@router.message(StateFilter(ListingCreate.media), F.photo)
async def add_photo(msg: Message, state: FSMContext):
    data = await state.get_data()
    media = data["draft"]["media"]
    if any(t == "video" for t, _ in media):
        await msg.answer("❌ Video bilan rasm aralashtirib bo'lmaydi.")
        return
    photos = [m for m in media if m[0] == "photo"]
    if len(photos) >= 2:
        await msg.answer("❌ Maksimum 2 ta rasm.")
        return
    file_id = msg.photo[-1].file_id
    media.append(("photo", file_id))
    data["draft"]["media"] = media
    await state.update_data(draft=data["draft"])
    await msg.answer(f"✅ Rasm qabul qilindi ({len(media)} ta). Yana yuborishingiz mumkin.", reply_markup=media_done_kb())


@router.message(StateFilter(ListingCreate.media), F.video)
async def add_video(msg: Message, state: FSMContext):
    data = await state.get_data()
    media = data["draft"]["media"]
    if media:
        await msg.answer("❌ Faqat 1 ta video yuborilishi mumkin va boshqa media bilan aralashmaydi.")
        return
    data["draft"]["media"] = [("video", msg.video.file_id)]
    await state.update_data(draft=data["draft"])
    await msg.answer("✅ Video qabul qilindi.", reply_markup=media_done_kb())


@router.callback_query(F.data == "media_reset", StateFilter(ListingCreate.media))
async def media_reset(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    data["draft"]["media"] = []
    await state.update_data(draft=data["draft"])
    await safe_edit(cb, "🔄 Media tozalandi. Qayta yuboring:", reply_markup=media_done_kb())
    await safe_answer(cb)


@router.callback_query(F.data == "media_done", StateFilter(ListingCreate.media))
async def media_done(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not validate_media_combo(data["draft"]["media"]):
        await safe_answer(cb, "❌ 1-2 rasm yoki 1 video yuboring", show_alert=True)
        return
    await state.set_state(ListingCreate.price)
    await safe_edit(cb, "7️⃣ <b>Narxni</b> so'mda kiriting (masalan: 350000):",
                    reply_markup=cancel_kb())
    await safe_answer(cb)


@router.message(StateFilter(ListingCreate.price), F.text)
async def set_price(msg: Message, state: FSMContext):
    v = parse_positive_int(msg.text, min_v=1000, max_v=1_000_000_000)
    if v is None:
        await msg.answer("❌ To'g'ri narx kiriting (kamida 1 000 so'm).")
        return
    data = await state.get_data()
    data["draft"]["price"] = v
    await state.update_data(draft=data["draft"])
    await state.set_state(ListingCreate.description)
    await msg.answer(
        "8️⃣ Qo'shimcha <b>tavsif</b> kiriting (ixtiyoriy).\n"
        "O'tkazib yuborish uchun <b>-</b> yuboring.",
        reply_markup=cancel_kb()
    )


@router.message(StateFilter(ListingCreate.description), F.text)
async def set_desc(msg: Message, state: FSMContext):
    text = msg.text.strip()
    data = await state.get_data()
    if text == "-":
        data["draft"]["description"] = None
    else:
        data["draft"]["description"] = text[:800]
    await state.update_data(draft=data["draft"])
    await state.set_state(ListingCreate.preview)
    preview = format_listing_preview(data["draft"])
    await msg.answer(preview, reply_markup=preview_kb())


@router.callback_query(F.data == "preview_edit", StateFilter(ListingCreate.preview))
async def preview_edit(cb: CallbackQuery, state: FSMContext):
    await safe_edit(cb, "✏️ Qaysi maydonni o'zgartirmoqchisiz?", reply_markup=preview_edit_kb())
    await safe_answer(cb)


@router.callback_query(F.data == "preview_back", StateFilter(ListingCreate.preview))
async def preview_back(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await safe_edit(cb, format_listing_preview(data["draft"]), reply_markup=preview_kb())
    await safe_answer(cb)


@router.callback_query(F.data.startswith("edit_field:"), StateFilter(ListingCreate.preview))
async def edit_field(cb: CallbackQuery, state: FSMContext):
    field = cb.data.split(":", 1)[1]
    data = await state.get_data()
    draft = data["draft"]
    if field == "current_rank":
        await state.set_state(ListingCreate.current_rank)
        await safe_edit(cb, "🏆 Hozirgi rankni tanlang:", reply_markup=ranks_kb("cr"))
    elif field == "peak_rank":
        await state.set_state(ListingCreate.peak_rank)
        await safe_edit(cb, "⭐ Peak rankni tanlang:", reply_markup=ranks_kb("pr"))
    elif field == "hero_count":
        await state.set_state(ListingCreate.hero_count)
        await safe_edit(cb, "🦸 Hero sonini kiriting:", reply_markup=cancel_kb())
    elif field == "skin_count":
        await state.set_state(ListingCreate.skin_count)
        await safe_edit(cb, "🎨 Skin sonini kiriting:", reply_markup=cancel_kb())
    elif field == "account_links":
        await state.set_state(ListingCreate.account_links)
        await safe_edit(cb, "🔗 Linklarni belgilang:", reply_markup=links_kb(draft["account_links"]))
    elif field == "media":
        draft["media"] = []
        await state.update_data(draft=draft)
        await state.set_state(ListingCreate.media)
        await safe_edit(cb, "📷 Media yuboring:", reply_markup=media_done_kb())
    elif field == "price":
        await state.set_state(ListingCreate.price)
        await safe_edit(cb, "💰 Narxni kiriting:", reply_markup=cancel_kb())
    elif field == "description":
        await state.set_state(ListingCreate.description)
        await safe_edit(cb, "📝 Tavsif kiriting (yoki - yuboring):", reply_markup=cancel_kb())
    await safe_answer(cb)


@router.callback_query(F.data == "publish_listing", StateFilter(ListingCreate.preview))
async def publish(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    draft = data["draft"]
    tg_id = cb.from_user.id

    # Validate draft
    if not all([draft["current_rank"], draft["peak_rank"], draft["hero_count"],
                draft["skin_count"], draft["price"], draft["media"]]):
        await safe_answer(cb, "❌ Ma'lumotlar to'liq emas", show_alert=True)
        return

    price = await settings_service.get_int("listing_create_price", 2000)
    bal = await balance_service.get_balance(tg_id)
    if bal < price:
        await safe_answer(cb, "Balans yetarli emas", show_alert=False)
        await cb.message.answer(
            "❌ <b>Balans yetarli emas</b>\n\n"
            f"E'lon joylash: <b>{price:,} so'm</b>\n".replace(",", " ") +
            f"Balansingiz: <b>{bal:,} so'm</b>\n\n".replace(",", " ") +
            "Avval balansingizni to'ldiring.\n\n"
            "Draft saqlandi — balans to'ldirilgach davom ettirishingiz mumkin.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💰 BALANSNI TO'LDIRISH", callback_data=f"bal_deposit:{listing.id}")],
            ])
        )
        # Save as draft
        try:
            listing = await listing_service.create_draft(
                tg_id,
                current_rank=draft["current_rank"],
                peak_rank=draft["peak_rank"],
                hero_count=draft["hero_count"],
                skin_count=draft["skin_count"],
                account_links=draft["account_links"],
                price=draft["price"],
                description=draft["description"] or "",
            )
            await listing_service.save_media(listing.id, draft["media"])
        except Exception:
            await cb.message.answer("❌ Draftni saqlab bo'lmadi. Qaytadan urinib ko'ring.")
            await state.clear()
            return

    # Publish
    await safe_answer(cb, "⏳ Joylanmoqda...")
    try:
        listing = await listing_service.create_draft(
            tg_id,
            current_rank=draft["current_rank"],
            peak_rank=draft["peak_rank"],
            hero_count=draft["hero_count"],
            skin_count=draft["skin_count"],
            account_links=draft["account_links"],
            price=draft["price"],
            description=draft["description"] or "",
        )
        await listing_service.save_media(listing.id, draft["media"])
    except Exception as e:
        await cb.message.answer(f"❌ Xatolik: {e}")
        await state.clear()
        return

    ok, msg = await listing_service.activate_and_publish(listing.id, tg_id)
    if ok:
        await cb.message.answer(
            f"✅ <b>E'lon #{listing.id} muvaffaqiyatli joylandi!</b>\n\n"
            "E'lon kanalga chiqarildi."
        )
    else:
        await cb.message.answer(f"❌ {msg}")
    await state.clear()


from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


@router.callback_query(F.data == "cancel_fsm")
async def cancel_fsm(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit(cb, "❌ Bekor qilindi.", reply_markup=None)
    await safe_answer(cb)


@router.callback_query(F.data == "cancel_confirm")
async def cancel_confirm(cb: CallbackQuery, state: FSMContext):
    await safe_edit(cb, "❌ Bekor qilindi.")
    await safe_answer(cb)