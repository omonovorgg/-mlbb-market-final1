from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from app.keyboards.user_kb import (
    my_listings_kb, listing_actions_kb, confirm_kb, back_kb
)
from app.utils.formatters import format_money
from app.services.listing_service import listing_service
from app.services.settings_service import settings_service
from app.services.balance_service import balance_service
from app.services.transaction_service import transaction_service
from app.services.channel_service import channel_service
from app.services.user_service import user_service
from app.utils.security import safe_edit, safe_answer
from app.states.states import EditListing

router = Router(name="my_listings")


@router.message(F.text == "📋 E'LONLARIM")
async def show_my_listings(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer("📋 <b>E'lonlarim</b>\n\nBo'limni tanlang:", reply_markup=my_listings_kb())


@router.callback_query(F.data.startswith("mylist:"))
async def list_by_status(cb: CallbackQuery):
    parts = cb.data.split(":", 1)
    if len(parts) < 2:
        return
    arg = parts[1]
    if arg == "back":
        await safe_edit(cb, "📋 <b>E'lonlarim</b>", reply_markup=my_listings_kb())
        await safe_answer(cb)
        return
    status = arg
    listings = await listing_service.user_listings(cb.from_user.id, status)
    if not listings:
        await safe_answer(cb, "Bo'sh", show_alert=False)
        await safe_edit(cb, f"📋 <b>{status}</b> bo'limida e'lonlar yo'q.", reply_markup=my_listings_kb())
        return
    await safe_edit(cb, f"📋 <b>{status}</b> — {len(listings)} ta:", reply_markup=_list_kb(listings))
    await safe_answer(cb)


def _list_kb(listings) -> InlineKeyboardMarkup:
    rows = []
    for l in listings[:20]:
        rows.append([InlineKeyboardButton(
            text=f"#{l.id} • {format_money(l.price)} • {l.current_rank}",
            callback_data=f"listing_open:{l.id}"
        )])
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="mylist:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data.startswith("listing_open:"))
async def open_listing(cb: CallbackQuery):
    lid = int(cb.data.split(":", 1)[1])
    l = await listing_service.get(lid)
    if not l:
        await safe_answer(cb, "E'lon topilmadi", show_alert=True)
        return
    u = await user_service.get_by_tg(cb.from_user.id)
    if not u or l.user_id != u.id:
        await safe_answer(cb, "Ruxsat yo'q", show_alert=True)
        return
    text = (
        f"📦 <b>E'LON #{l.id}</b>\n\n"
        f"💰 {format_money(l.price)}\n"
        f"🏆 {l.current_rank} → ⭐ {l.peak_rank}\n"
        f"🦸 {l.hero_count} Hero • 🎨 {l.skin_count} Skin\n"
        f"📊 Holat: <b>{l.status}</b>\n"
        f"✏️ Bepul edit: {'✅ ishlatilgan' if l.free_edit_used else '⬜ mavjud'}\n"
        f"💰 Bepul narx o'zgartirish: {'✅ ishlatilgan' if l.free_price_change_used else '⬜ mavjud'}"
    )
    await safe_edit(cb, text, reply_markup=listing_actions_kb(l.id, l.status, l.is_top))
    await safe_answer(cb)


@router.callback_query(F.data.startswith("sold:"))
async def mark_sold(cb: CallbackQuery):
    lid = int(cb.data.split(":", 1)[1])
    await safe_edit(cb, f"❓ E'lon #{lid} sotilgan deb belgilansinmi?",
                    reply_markup=confirm_kb(f"sold:{lid}"))
    await safe_answer(cb)


@router.callback_query(F.data.startswith("confirm:sold:"))
async def confirm_sold(cb: CallbackQuery):
    lid = int(cb.data.split(":", 2)[2])
    ok = await listing_service.mark_sold(lid, cb.from_user.id)
    await safe_edit(cb, "✅ Sotilgan deb belgilandi." if ok else "❌ Xatolik")
    await safe_answer(cb)


@router.callback_query(F.data.startswith("del:"))
async def del_listing(cb: CallbackQuery):
    lid = int(cb.data.split(":", 1)[1])
    await safe_edit(cb, f"❓ E'lon #{lid} o'chirilsinmi?",
                    reply_markup=confirm_kb(f"del:{lid}"))
    await safe_answer(cb)


@router.callback_query(F.data.startswith("confirm:del:"))
async def confirm_del(cb: CallbackQuery):
    lid = int(cb.data.split(":", 2)[2])
    ok = await listing_service.soft_delete(lid, cb.from_user.id)
    await safe_edit(cb, "🗑 O'chirildi." if ok else "❌ Xatolik")
    await safe_answer(cb)


@router.callback_query(F.data.startswith("top:"))
async def top_listing(cb: CallbackQuery):
    lid = int(cb.data.split(":", 1)[1])
    price = await settings_service.get_int("top_price", 10000)
    u = await user_service.get_by_tg(cb.from_user.id)
    if u.balance < price:
        await safe_answer(cb, f"Balans yetarli emas. Kerak: {price:,} so'm".replace(",", " "), show_alert=True)
        return
    await safe_edit(cb, f"🔥 TOP qilish — {price:,} so'm. Tasdiqlaysizmi?".replace(",", " "),
                    reply_markup=confirm_kb(f"top:{lid}"))
    await safe_answer(cb)


@router.callback_query(F.data.startswith("confirm:top:"))
async def confirm_top(cb: CallbackQuery):
    lid = int(cb.data.split(":", 2)[2])
    price = await settings_service.get_int("top_price", 10000)
    ok = await balance_service.atomic_debit(cb.from_user.id, price)
    if not ok:
        await safe_edit(cb, "❌ Balans yetarli emas")
        await safe_answer(cb)
        return
    await listing_service.update_fields(lid, cb.from_user.id, is_top=True)
    u = await user_service.get_by_tg(cb.from_user.id)
    await transaction_service.create(
        user_id=u.id, amount=-price, ttype="top_purchase",
        description=f"E'lon #{lid} TOP qilindi", related_listing_id=lid
    )
    await safe_edit(cb, "🔥 E'lon TOP qilindi!")
    await safe_answer(cb)


# -------- EDIT FLOW --------

@router.callback_query(F.data.startswith("edit:"))
async def start_edit(cb: CallbackQuery, state: FSMContext):
    lid = int(cb.data.split(":", 1)[1])
    l = await listing_service.get(lid)
    if not l:
        await safe_answer(cb, "Topilmadi", show_alert=True)
        return
    u = await user_service.get_by_tg(cb.from_user.id)
    if not u or l.user_id != u.id:
        await safe_answer(cb, "Ruxsat yo'q", show_alert=True)
        return

    free_count = await settings_service.get_int("free_edit_count", 1)
    price = await settings_service.get_int("listing_edit_price", 2000)
    is_free = (not l.free_edit_used) and free_count >= 1

    await state.update_data(edit_listing_id=lid, edit_is_free=is_free, edit_price=price)
    await state.set_state(EditListing.choosing_field)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏆 Rank", callback_data="editf:current_rank")],
        [InlineKeyboardButton(text="⭐ Peak", callback_data="editf:peak_rank")],
        [InlineKeyboardButton(text="🦸 Hero", callback_data="editf:hero_count")],
        [InlineKeyboardButton(text="🎨 Skin", callback_data="editf:skin_count")],
        [InlineKeyboardButton(text="🔗 Linklar", callback_data="editf:account_links")],
        [InlineKeyboardButton(text="📷 Media", callback_data="editf:media")],
        [InlineKeyboardButton(text="📝 Tavsif", callback_data="editf:description")],
        [InlineKeyboardButton(text="⬅️ Bekor", callback_data="cancel_fsm")],
    ])
    cost_txt = "🆓 Bepul" if is_free else f"💰 {price:,} so'm".replace(",", " ")
    await safe_edit(cb, f"✏️ Tahrirlash ({cost_txt})\n\nQaysi maydonni o'zgartirasiz?", reply_markup=kb)
    await safe_answer(cb)


@router.callback_query(F.data.startswith("editf:"), StateFilter(EditListing.choosing_field))
async def choose_edit_field(cb: CallbackQuery, state: FSMContext):
    field = cb.data.split(":", 1)[1]
    await state.update_data(edit_field=field)
    await state.set_state(EditListing.new_value)
    from app.keyboards.user_kb import ranks_kb, links_kb, media_done_kb, cancel_kb
    if field == "current_rank":
        await safe_edit(cb, "🏆 Yangi hozirgi rank:", reply_markup=ranks_kb("editcr"))
    elif field == "peak_rank":
        await safe_edit(cb, "⭐ Yangi peak rank:", reply_markup=ranks_kb("editpr"))
    elif field == "hero_count":
        await safe_edit(cb, "🦸 Yangi hero soni:", reply_markup=cancel_kb())
    elif field == "skin_count":
        await safe_edit(cb, "🎨 Yangi skin soni:", reply_markup=cancel_kb())
    elif field == "account_links":
        await safe_edit(cb, "🔗 Yangi linklar:", reply_markup=links_kb([]))
    elif field == "media":
        await safe_edit(cb, "📷 Yangi media (1-2 rasm yoki 1 video):", reply_markup=media_done_kb())
    elif field == "description":
        await safe_edit(cb, "📝 Yangi tavsif (yoki - yuboring):", reply_markup=cancel_kb())
    await safe_answer(cb)


@router.callback_query(F.data.startswith("editcr:"), StateFilter(EditListing.new_value))
async def edit_set_cr(cb: CallbackQuery, state: FSMContext):
    rank = cb.data.split(":", 1)[1]
    await state.update_data(edit_value=rank)
    await safe_edit(cb, f"✅ Rank: {rank}\n\nTasdiqlaysizmi?",
                    reply_markup=confirm_kb("applyedit"))
    await safe_answer(cb)


@router.callback_query(F.data.startswith("editpr:"), StateFilter(EditListing.new_value))
async def edit_set_pr(cb: CallbackQuery, state: FSMContext):
    rank = cb.data.split(":", 1)[1]
    await state.update_data(edit_value=rank)
    await safe_edit(cb, f"✅ Peak: {rank}\n\nTasdiqlaysizmi?",
                    reply_markup=confirm_kb("applyedit"))
    await safe_answer(cb)


@router.message(StateFilter(EditListing.new_value), F.text)
async def edit_set_text(msg: Message, state: FSMContext):
    data = await state.get_data()
    field = data["edit_field"]
    from app.utils.validators import parse_positive_int
    if field in ("hero_count", "skin_count"):
        v = parse_positive_int(msg.text, 1, 10000)
        if v is None:
            await msg.answer("❌ To'g'ri son kiriting.")
            return
        await state.update_data(edit_value=v)
    elif field == "description":
        text = msg.text.strip()
        await state.update_data(edit_value=None if text == "-" else text[:800])
    else:
        await state.update_data(edit_value=msg.text.strip())
    await msg.answer("✅ Tasdiqlaysizmi?", reply_markup=confirm_kb("applyedit"))


@router.message(StateFilter(EditListing.new_value), F.photo)
async def edit_set_photo(msg: Message, state: FSMContext):
    data = await state.get_data()
    if data.get("edit_field") != "media":
        return
    media = data.get("edit_media", [])
    if any(t == "video" for t, _ in media):
        await msg.answer("❌ Aralash bo'lmaydi.")
        return
    if len([m for m in media if m[0] == "photo"]) >= 2:
        await msg.answer("❌ Maksimum 2 rasm.")
        return
    media.append(("photo", msg.photo[-1].file_id))
    await state.update_data(edit_media=media)
    await msg.answer(f"✅ {len(media)} rasm qabul qilindi. Tasdiqlash uchun 'Media tayyor'ni bosing.",
                     reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                         [InlineKeyboardButton(text="✅ Media tayyor", callback_data="edit_media_done")],
                     ]))


@router.message(StateFilter(EditListing.new_value), F.video)
async def edit_set_video(msg: Message, state: FSMContext):
    data = await state.get_data()
    if data.get("edit_field") != "media":
        return
    await state.update_data(edit_media=[("video", msg.video.file_id)])
    await msg.answer("✅ Video qabul qilindi.",
                     reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                         [InlineKeyboardButton(text="✅ Media tayyor", callback_data="edit_media_done")],
                     ]))


@router.callback_query(F.data == "edit_media_done", StateFilter(EditListing.new_value))
async def edit_media_done(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    media = data.get("edit_media", [])
    from app.utils.validators import validate_media_combo
    if not validate_media_combo(media):
        await safe_answer(cb, "❌ 1-2 rasm yoki 1 video", show_alert=True)
        return
    await safe_edit(cb, "✅ Media tayyor. Tasdiqlaysizmi?",
                    reply_markup=confirm_kb("applyedit"))
    await safe_answer(cb)


@router.callback_query(F.data == "confirm:applyedit", StateFilter(EditListing.new_value))
async def apply_edit(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lid = data["edit_listing_id"]
    field = data["edit_field"]
    is_free = data["edit_is_free"]
    price = data["edit_price"]

    # Charge if not free
    if not is_free:
        ok = await balance_service.atomic_debit(cb.from_user.id, price)
        if not ok:
            await safe_edit(cb, "❌ Balans yetarli emas. Balansni to'ldiring.")
            await safe_answer(cb)
            return

    # Prepare updates
    updates = {}
    if field == "media":
        media = data.get("edit_media", [])
        await listing_service.save_media(lid, media)
    else:
        updates[field] = data["edit_value"]
        await listing_service.update_fields(lid, cb.from_user.id, **updates)

    # Mark free_edit_used
    if is_free:
        await listing_service.update_fields(lid, cb.from_user.id, free_edit_used=True)

    # Transaction
    if not is_free:
        u = await user_service.get_by_tg(cb.from_user.id)
        await transaction_service.create(
            user_id=u.id, amount=-price, ttype="listing_edit",
            description=f"E'lon #{lid} tahrirlash", related_listing_id=lid
        )

    # Update channel post
    try:
        await channel_service.edit_listing(lid)
    except Exception:
        pass

    await safe_edit(cb, "✅ Tahrirlandi va kanal yangilandi.")
    await safe_answer(cb)
    await state.clear()


# -------- PRICE CHANGE --------

@router.callback_query(F.data.startswith("pricech:"))
async def start_price_change(cb: CallbackQuery, state: FSMContext):
    lid = int(cb.data.split(":", 1)[1])
    l = await listing_service.get(lid)
    if not l:
        await safe_answer(cb, "Topilmadi", show_alert=True)
        return
    u = await user_service.get_by_tg(cb.from_user.id)
    if not u or l.user_id != u.id:
        await safe_answer(cb, "Ruxsat yo'q", show_alert=True)
        return
    await state.update_data(price_listing_id=lid)
    await state.set_state(EditListing.new_value)
    await state.update_data(edit_field="_price", edit_listing_id=lid)
    await safe_edit(cb, f"💰 Yangi narxni kiriting (hozir: {format_money(l.price)}):",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="❌ Bekor", callback_data="cancel_fsm")]
                    ]))
    await safe_answer(cb)


@router.message(StateFilter(EditListing.new_value), F.text)
async def apply_price_change(msg: Message, state: FSMContext):
    data = await state.get_data()
    if data.get("edit_field") != "_price":
        return
    from app.utils.validators import parse_positive_int
    v = parse_positive_int(msg.text, 1000, 1_000_000_000)
    if v is None:
        await msg.answer("❌ To'g'ri narx kiriting.")
        return
    lid = data["price_listing_id"]
    l = await listing_service.get(lid)
    free_count = await settings_service.get_int("free_price_change_count", 1)
    price = await settings_service.get_int("price_change_price", 2000)
    is_free = (not l.free_price_change_used) and free_count >= 1
    await state.update_data(edit_value=v, edit_is_free=is_free, edit_price=price, edit_field="price")
    cost = "🆓 Bepul" if is_free else f"💰 {price:,} so'm".replace(",", " ")
    await msg.answer(
        f"Yangi narx: <b>{format_money(v)}</b>\n{cost}\n\nTasdiqlaysizmi?",
        reply_markup=confirm_kb(f"applyprice:{lid}")
    )


@router.callback_query(F.data.startswith("confirm:applyprice:"))
async def confirm_price_change(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lid = int(cb.data.split(":", 2)[2])
    new_price = data["edit_value"]
    is_free = data["edit_is_free"]
    price = data["edit_price"]

    if not is_free:
        ok = await balance_service.atomic_debit(cb.from_user.id, price)
        if not ok:
            await safe_edit(cb, "❌ Balans yetarli emas.")
            await safe_answer(cb)
            return

    old = await listing_service.get(lid)
    old_price = old.price if old else 0
    await listing_service.update_fields(lid, cb.from_user.id, price=new_price)
    if is_free:
        await listing_service.update_fields(lid, cb.from_user.id, free_price_change_used=True)

    if not is_free:
        u = await user_service.get_by_tg(cb.from_user.id)
        await transaction_service.create(
            user_id=u.id, amount=-price, ttype="price_change",
            description=f"E'lon #{lid} narxi o'zgartirildi", related_listing_id=lid
        )

    try:
        await channel_service.edit_listing(lid)
    except Exception:
        pass

    await safe_edit(cb,
                    f"✅ Narx yangilandi: {format_money(old_price)} → {format_money(new_price)}")
    await safe_answer(cb)
    await state.clear()