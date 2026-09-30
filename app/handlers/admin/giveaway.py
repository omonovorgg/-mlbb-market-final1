import asyncio

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError, TelegramBadRequest

from app.filters.admin_filter import AdminFilter
from app.states.states import AdminStates
from app.database.db import async_session
from app.database.models import Giveaway
from app.database.repository import GiveawayRepo, UserRepo
from app.keyboards.admin_kb import admin_back_kb
from app.utils.security import safe_edit, safe_answer
from app.services.giveaway_service import giveaway_service, giveaway_kb


router = Router(name="admin_giveaway")
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


def _menu(active: bool) -> InlineKeyboardMarkup:
    rows = []
    if active:
        rows.append([InlineKeyboardButton(text="📊 Faol konkursni ko‘rish", callback_data="adg:view")])
        rows.append([InlineKeyboardButton(text="⛔ Konkursni tugatish", callback_data="adg:stop")])
    rows.append([InlineKeyboardButton(text="➕ Yangi konkurs yaratish", callback_data="adg:create")])
    rows.append([InlineKeyboardButton(text="⬅️ Admin panel", callback_data="ad:panel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "ad:giveaway")
async def giveaway_menu(cb: CallbackQuery):
    active = await giveaway_service.get_active()
    await safe_edit(
        cb,
        "🎁 <b>KONKURS</b>\n\n"
        + ("🟢 Hozir faol konkurs bor." if active else "🔴 Hozir faol konkurs yo‘q."),
        reply_markup=_menu(bool(active)),
    )
    await safe_answer(cb)


@router.callback_query(F.data == "adg:create")
async def giveaway_create(cb: CallbackQuery, state: FSMContext):
    active = await giveaway_service.get_active()
    if active:
        await cb.answer("Avval faol konkursni tugating.", show_alert=True)
        return
    await state.clear()
    await state.set_state(AdminStates.giveaway_video)
    await safe_edit(
        cb,
        "🎁 <b>Yangi konkurs</b>\n\n"
        "1/2 — Konkurs videosini yuboring.\n"
        "Faqat video yuboring.",
        reply_markup=admin_back_kb(),
    )
    await safe_answer(cb)


@router.message(AdminStates.giveaway_video, F.video)
async def giveaway_video(msg: Message, state: FSMContext):
    await state.update_data(giveaway_video=msg.video.file_id)
    await state.set_state(AdminStates.giveaway_text)
    await msg.answer(
        "2/2 — Endi konkurs uchun matnni yuboring.\n\n"
        "Masalan:\n"
        "<b>🎁 MLBB AKKAUNT KONKURSI</b>\n"
        "Qatnashish bepul. G‘olib random orqali aniqlanadi."
    )


@router.message(AdminStates.giveaway_video)
async def giveaway_video_invalid(msg: Message):
    await msg.answer("❌ Video yuboring. Boshqa fayl qabul qilinmaydi.")


@router.message(AdminStates.giveaway_text, F.text)
async def giveaway_text(msg: Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(giveaway_text=msg.html_text)
    await state.set_state(AdminStates.giveaway_confirm)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 BOSHLASH VA BARCHAGA YUBORISH", callback_data="adg:confirm")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="ad:panel")],
    ])
    await msg.answer_video(data["giveaway_video"])
    await msg.answer(
        f"🎁 <b>KONKURS PREVIEW</b>\n\n{msg.html_text}\n\n"
        "👥 Qatnashchilar: <b>0</b>\n\n"
        "Tugmani bosgan foydalanuvchi konkursga qo‘shiladi.",
        reply_markup=kb,
    )


@router.message(AdminStates.giveaway_text)
async def giveaway_text_invalid(msg: Message):
    await msg.answer("❌ Konkurs matnini oddiy xabar sifatida yuboring.")


@router.callback_query(F.data == "adg:confirm", AdminStates.giveaway_confirm)
async def giveaway_confirm(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    video_id = data.get("giveaway_video")
    text = data.get("giveaway_text", "").strip()
    if not video_id or not text:
        await state.clear()
        await cb.answer("❌ Konkurs ma‘lumotlari to‘liq emas.", show_alert=True)
        return

    async with async_session() as session:
        old = await GiveawayRepo.get_active(session)
        if old:
            await cb.answer("❌ Faol konkurs allaqachon mavjud.", show_alert=True)
            return
        giveaway = await GiveawayRepo.create(session, video_file_id=video_id, text=text)
        await session.commit()

    await state.clear()
    await safe_answer(cb, "⏳ Konkurs ishga tushyapti...")
    sent, failed = await giveaway_service.broadcast(cb.bot, giveaway)
    await cb.message.answer(
        "🎁 <b>Konkurs ishga tushdi!</b>\n\n"
        f"📨 Yuborildi: <b>{sent}</b>\n"
        f"❌ Yuborilmadi: <b>{failed}</b>\n"
        "👥 Boshlang‘ich real qatnashchilar: <b>0</b>",
        reply_markup=admin_back_kb(),
    )


@router.callback_query(F.data == "adg:view")
async def giveaway_view(cb: CallbackQuery):
    giveaway = await giveaway_service.get_active()
    if not giveaway:
        await cb.answer("Faol konkurs yo‘q.", show_alert=True)
        return
    count = await giveaway_service.participant_count(giveaway.id)
    await cb.message.answer_video(giveaway.video_file_id)
    await cb.message.answer(
        f"🎁 <b>FAOL KONKURS</b>\n\n{giveaway.text}\n\n👥 Qatnashchilar: <b>{count}</b>",
        reply_markup=giveaway_kb(count),
    )
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
