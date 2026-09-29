from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from app.filters.admin_filter import RoleFilter
from app.database.db import async_session
from app.database.repository import CardRepo
from app.states.states import CardStates
from app.keyboards.admin_kb import admin_cards_kb
from app.utils.security import safe_edit, safe_answer

router = Router(name="admin_cards")
router.callback_query.filter(RoleFilter("SUPER_ADMIN"))
router.message.filter(RoleFilter("SUPER_ADMIN"))

def _card_kb(card_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ O'zgartirish", callback_data=f"adcard:edit:{card_id}")],
        [InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"adcard:del:{card_id}")],
        [InlineKeyboardButton(text="⬅️ Kartalar", callback_data="ad:cards")],
    ])

@router.callback_query(F.data == "ad:cards")
async def cards_menu(cb: CallbackQuery):
    await safe_edit(cb, "💳 <b>To'lov kartalari</b>", reply_markup=admin_cards_kb())
    await safe_answer(cb)

@router.callback_query(F.data == "adcard:list")
async def cards_list(cb: CallbackQuery):
    async with async_session() as session:
        cards = await CardRepo.all(session)
    if not cards:
        text = "💳 <b>Kartalar yo'q.</b>"
        kb = admin_cards_kb()
    else:
        lines = ["💳 <b>To'lov kartalari:</b>"]
        rows = []
        for c in cards:
            status = "🟢" if c.active else "🔴"
            bank = f" · {c.bank_name}" if c.bank_name else ""
            lines.append(f"{status} #{c.id} · <code>{c.card_number}</code> · {c.holder_name}{bank}")
            rows.append([InlineKeyboardButton(text=f"⚙️ #{c.id}", callback_data=f"adcard:view:{c.id}")])
        rows.append([InlineKeyboardButton(text="➕ Karta qo'shish", callback_data="adcard:add")])
        rows.append([InlineKeyboardButton(text="⬅️ Admin panel", callback_data="ad:panel")])
        kb = InlineKeyboardMarkup(inline_keyboard=rows)
        text = "\n".join(lines)
    await safe_edit(cb, text, reply_markup=kb)
    await safe_answer(cb)

@router.callback_query(F.data.startswith("adcard:view:"))
async def card_view(cb: CallbackQuery):
    cid = int(cb.data.rsplit(":", 1)[1])
    async with async_session() as session:
        c = await CardRepo.get(session, cid)
    if not c:
        await safe_answer(cb, "Karta topilmadi", show_alert=True)
        return
    status = "🟢 Aktiv" if c.active else "🔴 Nofaol"
    await safe_edit(
        cb,
        f"💳 <b>Karta #{c.id}</b>\n\n<blockquote>💳 {c.card_number}\n👤 {c.holder_name}\n🏦 {c.bank_name or '—'}\n📌 {status}</blockquote>",
        reply_markup=_card_kb(c.id),
    )
    await safe_answer(cb)

@router.callback_query(F.data == "adcard:add")
async def card_add(cb: CallbackQuery, state: FSMContext):
    await state.set_state(CardStates.add_number)
    await safe_edit(
        cb,
        "➕ <b>Karta qo'shish</b>\n\nKarta raqamini yuboring:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="❌ Bekor", callback_data="ad:cards")]]
        ),
    )
    await safe_answer(cb)

@router.message(CardStates.add_number, F.text)
async def card_add_number(msg: Message, state: FSMContext):
    number = " ".join(msg.text.split())
    if len("".join(ch for ch in number if ch.isdigit())) < 12:
        await msg.answer("❌ Karta raqami noto'g'ri.")
        return
    await state.update_data(card_number=number)
    await state.set_state(CardStates.add_holder)
    await msg.answer("👤 Karta egasi ismini yuboring:")

@router.message(CardStates.add_holder, F.text)
async def card_add_holder(msg: Message, state: FSMContext):
    await state.update_data(holder_name=msg.text.strip())
    await state.set_state(CardStates.add_bank)
    await msg.answer("🏦 Bank nomi (masalan: Ipak Yo'li):")

@router.message(CardStates.add_bank, F.text)
async def card_add_bank(msg: Message, state: FSMContext):
    d = await state.get_data()
    async with async_session() as session:
        c = await CardRepo.create(session, d["card_number"], d["holder_name"], msg.text.strip())
        await session.commit()
    await msg.answer(f"✅ Karta #{c.id} qo'shildi.")
    await state.clear()

@router.callback_query(F.data.startswith("adcard:del:"))
async def card_delete(cb: CallbackQuery):
    cid = int(cb.data.rsplit(":", 1)[1])
    async with async_session() as session:
        ok = await CardRepo.delete(session, cid)
        await session.commit()
    await safe_edit(cb, "✅ Karta o'chirildi." if ok else "❌ Karta topilmadi.", reply_markup=admin_cards_kb())
    await safe_answer(cb)

@router.callback_query(F.data.startswith("adcard:edit:"))
async def card_edit_prompt(cb: CallbackQuery, state: FSMContext):
    cid = int(cb.data.rsplit(":", 1)[1])
    await state.set_state(CardStates.edit_card)
    await state.update_data(edit_card_id=cid)
    await safe_edit(
        cb,
        "✏️ Yangi ma'lumotni bitta qatorda yuboring:\n<code>karta raqami | egasi | bank</code>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="❌ Bekor", callback_data="ad:cards")]]
        ),
    )
    await safe_answer(cb)

@router.message(CardStates.edit_card, F.text)
async def card_edit_save(msg: Message, state: FSMContext):
    d = await state.get_data()
    parts = [x.strip() for x in msg.text.split("|")]
    if len(parts) != 3 or len("".join(ch for ch in parts[0] if ch.isdigit())) < 12:
        await msg.answer("❌ Format: karta raqami | egasi | bank")
        return
    async with async_session() as session:
        c = await CardRepo.update(session, d["edit_card_id"], parts[0], parts[1], parts[2])
        await session.commit()
    await msg.answer("✅ Karta yangilandi." if c else "❌ Karta topilmadi.")
    await state.clear()
