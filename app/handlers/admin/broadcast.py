import asyncio
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError, TelegramBadRequest
from app.filters.admin_filter import AdminFilter
from app.states.states import AdminStates
from app.services.admin_log_service import admin_log_service
from app.database.db import async_session
from app.database.repository import UserRepo
from app.keyboards.admin_kb import admin_back_kb, admin_confirm_kb
from app.utils.security import safe_edit, safe_answer
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

router = Router(name="admin_broadcast")
router.callback_query.filter(AdminFilter())
router.message.filter(AdminFilter())


@router.callback_query(F.data == "ad:broadcast")
async def broadcast_start(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.broadcast_message)
    await safe_edit(cb, "📣 <b>Barchaga xabar</b>\n\nXabar matnini kiriting:",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="❌ Bekor", callback_data="ad:panel")]
                    ]))
    await safe_answer(cb)


@router.message(AdminStates.broadcast_message, F.text)
async def broadcast_preview(msg: Message, state: FSMContext):
    await state.update_data(broadcast_text=msg.html_text)
    async with async_session() as session:
        ids = await UserRepo.all_ids(session)
    await state.set_state(AdminStates.broadcast_confirm)
    await msg.answer(
        f"📣 <b>Preview:</b>\n\n{msg.html_text}\n\n"
        f"👥 Qabul qiluvchilar: <b>{len(ids)}</b>\n\nTasdiqlaysizmi?",
        reply_markup=admin_confirm_kb("broadcast")
    )


@router.callback_query(F.data == "adconfirm:broadcast", AdminStates.broadcast_confirm)
async def broadcast_send(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    text = data.get("broadcast_text", "")
    await state.clear()
    await safe_answer(cb, "⏳ Yuborilmoqda...")
    async with async_session() as session:
        ids = await UserRepo.all_ids(session)
    sent, failed = 0, 0
    for uid in ids:
        try:
            await cb.bot.send_message(uid, text)
            sent += 1
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
            try:
                await cb.bot.send_message(uid, text)
                sent += 1
            except Exception:
                failed += 1
        except (TelegramForbiddenError, TelegramBadRequest):
            failed += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)
    await admin_log_service.log(cb.from_user.id, "broadcast", f"{sent}/{len(ids)}", text[:100])
    await cb.message.answer(f"✅ Yuborildi: {sent}\n❌ Xato: {failed}")