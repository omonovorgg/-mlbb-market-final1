import json
import random
from sqlalchemy import select

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from app.filters.admin_filter import AdminFilter
from app.states.states import AdminStates
from app.database.db import async_session
from app.database.models import Giveaway, GiveawayParticipant
from app.database.repository import GiveawayRepo
from app.keyboards.admin_kb import admin_back_kb
from app.utils.security import safe_edit, safe_answer
from app.services.giveaway_service import giveaway_service, giveaway_kb
from app.services.settings_service import settings_service

router = Router(name="admin_giveaway")
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


def _menu(active: bool) -> InlineKeyboardMarkup:
    rows = []
    if active:
        rows += [
            [InlineKeyboardButton(text="📊 Faol konkursni ko‘rish", callback_data="adg:view")],
            [InlineKeyboardButton(text="👥 Qatnashchilar", callback_data="adg:participants")],
            [InlineKeyboardButton(text="🎲 Tasodifiy g‘olib", callback_data="adg:winner:random")],
            [InlineKeyboardButton(text="✍️ Qo‘lda g‘olib tanlash", callback_data="adg:winner:manual")],
            [InlineKeyboardButton(text="⛔ Konkursni tugatish", callback_data="adg:stop")],
        ]
    rows += [
        [InlineKeyboardButton(text="➕ Yangi konkurs yaratish", callback_data="adg:create")],
        [InlineKeyboardButton(text="📢 Konkurs kanalini sozlash", callback_data="adg:target")],
        [InlineKeyboardButton(text="📋 Majburiy kanallar", callback_data="adg:channels")],
        [InlineKeyboardButton(text="⬅️ Admin panel", callback_data="ad:panel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _catalog() -> list[str]:
    try:
        value = json.loads(await settings_service.get("giveaway_channel_catalog", "[]"))
        return [str(x) for x in value]
    except Exception:
        return []


async def _save_catalog(items: list[str]):
    await settings_service.set("giveaway_channel_catalog", json.dumps(list(dict.fromkeys(items))))


async def _setup_kb(state: FSMContext) -> InlineKeyboardMarkup:
    data = await state.get_data()
    catalog = await _catalog()
    selected = set(data.get("giveaway_required_channels", []))
    rows = []
    for i, channel in enumerate(catalog):
        mark = "✅" if channel in selected else "▫️"
        rows.append([InlineKeyboardButton(text=f"{mark} {channel}", callback_data=f"adg:toggle:{i}")])
    rows += [
        [InlineKeyboardButton(text="➕ Yangi kanal qo‘shish", callback_data="adg:channel:add")],
        [InlineKeyboardButton(text="📢 Konkurs kanalini belgilash", callback_data="adg:target")],
        [InlineKeyboardButton(text="👁 Preview", callback_data="adg:preview")],
        [InlineKeyboardButton(text="🚀 Konkursni kanalga joylash", callback_data="adg:publish")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="ad:giveaway")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _setup_text(state: FSMContext) -> str:
    data = await state.get_data()
    target = await settings_service.get("giveaway_target_channel", "")
    selected = data.get("giveaway_required_channels", [])
    return (
        "🎁 <b>KONKURS SOZLAMALARI</b>\n\n"
        f"📢 Konkurs joylanadigan kanal: <code>{target or 'Belgilanmagan'}</code>\n"
        f"🔒 Majburiy obuna kanallari: <b>{len(selected)} ta</b>\n\n"
        "Kerakli kanallarni tanlang. Yangi kanal qo‘shishingiz ham mumkin."
    )


@router.callback_query(F.data == "ad:giveaway")
async def giveaway_menu(cb: CallbackQuery):
    active = await giveaway_service.get_active()
    await safe_edit(cb, "🎁 <b>KONKURS BOSHQARUVI</b>\n\n" +
                    ("🟢 Hozir faol konkurs bor." if active else "🔴 Hozir faol konkurs yo‘q."),
                    reply_markup=_menu(bool(active)))
    await safe_answer(cb)


@router.callback_query(F.data == "adg:create")
async def giveaway_create(cb: CallbackQuery, state: FSMContext):
    if await giveaway_service.get_active():
        await cb.answer("Avval faol konkursni tugating.", show_alert=True)
        return
    await state.clear()
    await state.set_state(AdminStates.giveaway_video)
    await safe_edit(cb,
        "🎁 <b>Yangi konkurs</b>\n\n"
        "Konkurs uchun <b>bitta xabarda</b> rasm yoki video va uning caption matnini yuboring.\n"
        "Matnni alohida yuborish shart emas.",
        reply_markup=admin_back_kb())
    await safe_answer(cb)


@router.message(AdminStates.giveaway_video, F.photo)
@router.message(AdminStates.giveaway_video, F.video)
async def giveaway_media(msg: Message, state: FSMContext):
    if msg.photo:
        media_type = "photo"
        file_id = msg.photo[-1].file_id
    else:
        media_type = "video"
        file_id = msg.video.file_id
    caption = (msg.html_text or "").strip()
    if not caption:
        await msg.answer("❌ Rasm yoki videoga caption matnini qo‘shib qayta yuboring.")
        return
    try:
        from app.services.media_archive_service import media_archive_service
        file_id = await media_archive_service.archive_file(msg.bot, file_id, media_type, caption) or file_id
    except Exception:
        pass
    await state.update_data(giveaway_video=file_id, giveaway_media_type=media_type,
                            giveaway_text=caption, giveaway_required_channels=[])
    await state.set_state(AdminStates.giveaway_text)
    await msg.answer(await _setup_text(state), reply_markup=await _setup_kb(state))


@router.message(AdminStates.giveaway_video)
async def giveaway_media_invalid(msg: Message):
    await msg.answer("❌ Bitta xabarda rasm yoki video va caption yuboring.")


@router.callback_query(F.data == "adg:channels")
async def giveaway_channels_menu(cb: CallbackQuery, state: FSMContext):
    if not await state.get_data():
        await state.update_data(giveaway_required_channels=[])
    await state.set_state(AdminStates.giveaway_text)
    await safe_edit(cb, "📋 <b>Majburiy obuna kanallari</b>\nKonkurs yaratishda kerakli kanallarni belgilang yoki yangisini qo‘shing.",
                    reply_markup=await _setup_kb(state))
    await safe_answer(cb)


@router.callback_query(F.data.startswith("adg:toggle:"), AdminStates.giveaway_text)
async def giveaway_toggle_channel(cb: CallbackQuery, state: FSMContext):
    index = int(cb.data.rsplit(":", 1)[1])
    catalog = await _catalog()
    if index < 0 or index >= len(catalog):
        await cb.answer("Kanal topilmadi.", show_alert=True)
        return
    data = await state.get_data()
    selected = list(data.get("giveaway_required_channels", []))
    channel = catalog[index]
    if channel in selected:
        selected.remove(channel)
    else:
        selected.append(channel)
    await state.update_data(giveaway_required_channels=selected)
    await safe_edit(cb, await _setup_text(state), reply_markup=await _setup_kb(state))
    await safe_answer(cb)


@router.callback_query(F.data == "adg:channel:add")
async def giveaway_add_channel_start(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.giveaway_required_add)
    await safe_edit(cb, "Yangi majburiy kanalning @username yoki -100... ID sini yuboring. Bot u kanalda admin bo‘lishi kerak.",
                    reply_markup=admin_back_kb())
    await safe_answer(cb)


@router.message(AdminStates.giveaway_required_add, F.text)
async def giveaway_add_channel_finish(msg: Message, state: FSMContext):
    raw = msg.text.strip()
    target = int(raw) if raw.lstrip("-").isdigit() else raw
    try:
        chat = await msg.bot.get_chat(target)
        me = await msg.bot.get_me()
        member = await msg.bot.get_chat_member(chat.id, me.id)
        if member.status not in {"administrator", "creator"}:
            await msg.answer("❌ Bot bu kanalda administrator emas.")
            return
        channel = str(chat.id)
        catalog = await _catalog()
        if channel not in catalog:
            catalog.append(channel)
            await _save_catalog(catalog)
        data = await state.get_data()
        selected = list(data.get("giveaway_required_channels", []))
        if channel not in selected:
            selected.append(channel)
        await state.update_data(giveaway_required_channels=selected)
        await state.set_state(AdminStates.giveaway_text)
        await msg.answer(await _setup_text(state), reply_markup=await _setup_kb(state))
    except Exception as exc:
        await msg.answer(f"❌ Kanalni tekshirib bo‘lmadi: <code>{str(exc)[:180]}</code>")


@router.callback_query(F.data == "adg:target")
async def giveaway_target_start(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.giveaway_target_channel)
    await safe_edit(cb, "Konkurs postlari chiqadigan kanalning @username yoki -100... ID sini yuboring. Bot admin va post yuborish huquqiga ega bo‘lsin.",
                    reply_markup=admin_back_kb())
    await safe_answer(cb)


@router.message(AdminStates.giveaway_target_channel, F.text)
async def giveaway_target_finish(msg: Message, state: FSMContext):
    raw = msg.text.strip()
    target = int(raw) if raw.lstrip("-").isdigit() else raw
    try:
        chat = await msg.bot.get_chat(target)
        me = await msg.bot.get_me()
        member = await msg.bot.get_chat_member(chat.id, me.id)
        if member.status not in {"administrator", "creator"} or getattr(member, "can_post_messages", True) is False:
            await msg.answer("❌ Botga kanalda administrator va post yuborish huquqi kerak.")
            return
        await settings_service.set("giveaway_target_channel", str(chat.id))
        await state.set_state(AdminStates.giveaway_text)
        await msg.answer("✅ Konkurs kanali saqlandi.\n\n" + await _setup_text(state),
                         reply_markup=await _setup_kb(state))
    except Exception as exc:
        await msg.answer(f"❌ Kanalni ulab bo‘lmadi: <code>{str(exc)[:180]}</code>")


@router.callback_query(F.data == "adg:preview", AdminStates.giveaway_text)
async def giveaway_preview(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    text = data.get("giveaway_text", "")
    media_type = data.get("giveaway_media_type")
    file_id = data.get("giveaway_video")
    if media_type == "photo":
        await cb.message.answer_photo(file_id, caption=text)
    else:
        await cb.message.answer_video(file_id, caption=text)
    await safe_answer(cb, "Preview yuborildi.")


@router.callback_query(F.data == "adg:publish", AdminStates.giveaway_text)
async def giveaway_publish(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    target = await settings_service.get("giveaway_target_channel", "")
    file_id = data.get("giveaway_video")
    caption = (data.get("giveaway_text") or "").strip()
    media_type = data.get("giveaway_media_type", "video")
    if not target or not file_id or not caption:
        await cb.answer("Media, caption va konkurs kanali to‘liq bo‘lishi kerak.", show_alert=True)
        return
    async with async_session() as session:
        if await GiveawayRepo.get_active(session):
            await cb.answer("Faol konkurs allaqachon bor.", show_alert=True)
            return
        giveaway = await GiveawayRepo.create(
            session, video_file_id=file_id, text=caption, media_type=media_type,
            target_channel_id=target,
            required_channels=json.dumps(data.get("giveaway_required_channels", []))
        )
        await session.commit()
        await session.refresh(giveaway)
    try:
        message_id = await giveaway_service.publish(cb.bot, giveaway)
    except Exception as exc:
        async with async_session() as session:
            current = await session.get(Giveaway, giveaway.id)
            if current:
                current.active = False
                await session.commit()
        await cb.answer(f"Kanalga post joylanmadi: {str(exc)[:180]}", show_alert=True)
        return
    await state.clear()
    await safe_answer(cb, "Konkurs kanalga joylandi!")
    await cb.message.answer(
        f"🎉 <b>Konkurs kanalga joylandi!</b>\nPost ID: <code>{message_id}</code>\n"
        f"Majburiy kanallar: <b>{len(data.get('giveaway_required_channels', []))}</b>",
        reply_markup=admin_back_kb())


@router.callback_query(F.data == "adg:view")
async def giveaway_view(cb: CallbackQuery):
    giveaway = await giveaway_service.get_active()
    if not giveaway:
        await cb.answer("Faol konkurs yo‘q.", show_alert=True)
        return
    count = await giveaway_service.participant_count(giveaway.id)
    if giveaway.media_type == "photo":
        await cb.message.answer_photo(giveaway.video_file_id, caption=giveaway.text, reply_markup=giveaway_kb(count))
    else:
        await cb.message.answer_video(giveaway.video_file_id, caption=giveaway.text, reply_markup=giveaway_kb(count))
    await safe_answer(cb)


@router.callback_query(F.data == "adg:stop")
async def giveaway_stop(cb: CallbackQuery):
    async with async_session() as session:
        giveaway = await GiveawayRepo.get_active(session)
        if not giveaway:
            await cb.answer("Faol konkurs yo‘q.", show_alert=True)
            return
        giveaway.active = False
        await session.commit()
    await safe_answer(cb, "Konkurs tugatildi.")
    await cb.message.answer("⛔ Konkurs tugatildi.", reply_markup=admin_back_kb())


@router.callback_query(F.data == "adg:participants")
async def giveaway_participants(cb: CallbackQuery):
    async with async_session() as session:
        g = await GiveawayRepo.get_active(session)
        if not g:
            await cb.answer("Faol konkurs yo‘q.", show_alert=True); return
        q = await session.execute(select(GiveawayParticipant).where(GiveawayParticipant.giveaway_id == g.id).order_by(GiveawayParticipant.joined_at.desc()).limit(100))
        users = q.scalars().all()
        count = await GiveawayRepo.participant_count(session, g.id)
    lines = [f"👥 QATNASHCHILAR: {count}", ""] + [f"• <code>{p.telegram_id}</code>" for p in users]
    if count > len(users): lines.append(f"... yana {count-len(users)} ta")
    await safe_edit(cb, "\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Orqaga", callback_data="ad:giveaway")]]))
    await safe_answer(cb)


@router.callback_query(F.data == "adg:winner:random")
async def giveaway_random_winner(cb: CallbackQuery):
    async with async_session() as session:
        g = await GiveawayRepo.get_active(session)
        if not g: await cb.answer("Faol konkurs yo‘q.", show_alert=True); return
        q = await session.execute(select(GiveawayParticipant.telegram_id).where(GiveawayParticipant.giveaway_id == g.id))
        ids = [x[0] for x in q.all()]
    if not ids: await cb.answer("Qatnashchilar yo‘q.", show_alert=True); return
    winner = random.SystemRandom().choice(ids)
    await cb.message.answer(f"🎲 <b>TASODIFIY TANLOV</b>\n🏆 G‘olib: <a href=\"tg://user?id={winner}\">{winner}</a>\n👥 Jami: {len(ids)}")
    await safe_answer(cb, "G‘olib tanlandi.")


@router.callback_query(F.data == "adg:winner:manual")
async def giveaway_manual_start(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.giveaway_manual_winner)
    await safe_edit(cb, "G‘olib qilinadigan qatnashchining Telegram ID sini yuboring.", reply_markup=admin_back_kb())
    await safe_answer(cb)


@router.message(AdminStates.giveaway_manual_winner, F.text)
async def giveaway_manual_finish(msg: Message, state: FSMContext):
    if not msg.text.strip().isdigit(): await msg.answer("Telegram ID raqamini yuboring."); return
    tg_id = int(msg.text.strip())
    async with async_session() as session:
        g = await GiveawayRepo.get_active(session)
        valid = bool(g and await GiveawayRepo.is_participant(session, g.id, tg_id))
    if not valid: await msg.answer("Bu ID faol konkurs qatnashchisi emas."); return
    await state.clear()
    await msg.answer(f"✍️ <b>ADMIN TANLOVI</b>\n🏆 Tanlangan qatnashchi: <a href=\"tg://user?id={tg_id}\">{tg_id}</a>")
