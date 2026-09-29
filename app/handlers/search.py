from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from app.keyboards.user_kb import search_menu_kb, sort_kb, ranks_kb
from app.utils.formatters import format_listing_card
from app.utils.validators import parse_positive_int
from app.services.listing_service import listing_service
from app.states.states import SearchStates
from app.utils.security import safe_edit, safe_answer

router = Router(name="search")

FILTER_KEY = "search_filter"


@router.message(F.text == "🔎 AKKAUNTLAR QIDIRISH")
async def search_entry(msg: Message, state: FSMContext):
    await state.clear()
    await state.set_state(SearchStates.menu)
    await state.update_data(search_filter={})
    await msg.answer("🔎 <b>Qidiruv</b>\n\nFiltrlarni tanlang:", reply_markup=search_menu_kb())


@router.callback_query(F.data.startswith("search:"), StateFilter(SearchStates.menu))
async def search_action(cb: CallbackQuery, state: FSMContext):
    action = cb.data.split(":", 1)[1]
    data = await state.get_data()
    flt = data.get("search_filter", {})

    if action == "clear":
        flt = {}
        await state.update_data(search_filter=flt)
        await safe_edit(cb, "🔄 Filtr tozalandi.", reply_markup=search_menu_kb())
        await safe_answer(cb)
        return

    if action == "price":
        await state.set_state(SearchStates.price_min)
        await safe_edit(cb, "💰 Minimal narxni kiriting (so'm):",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="search_back")]
                        ]))
    elif action == "hero":
        await state.set_state(SearchStates.hero_min)
        await safe_edit(cb, "🦸 Minimal hero soni:",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="search_back")]
                        ]))
    elif action == "skin":
        await state.set_state(SearchStates.skin_min)
        await safe_edit(cb, "🎨 Minimal skin soni:",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="search_back")]
                        ]))
    elif action == "currank":
        await safe_edit(cb, "🏆 Hozirgi rankni tanlang:",
                        reply_markup=ranks_kb("scr"))
    elif action == "peakrank":
        await safe_edit(cb, "⭐ Peak rankni tanlang:",
                        reply_markup=ranks_kb("spr"))
    elif action == "link":
        from app.keyboards.user_kb import links_kb
        await safe_edit(cb, "🔗 Linkni tanlang:", reply_markup=links_kb([]))
    elif action == "all":
        await safe_edit(cb, "🆕 Saralash:", reply_markup=sort_kb())
    await safe_answer(cb)


@router.callback_query(F.data == "search_back", StateFilter(SearchStates))
async def search_back(cb: CallbackQuery, state: FSMContext):
    await state.set_state(SearchStates.menu)
    await safe_edit(cb, "🔎 <b>Qidiruv</b>", reply_markup=search_menu_kb())
    await safe_answer(cb)


@router.message(StateFilter(SearchStates.price_min), F.text)
async def search_price_min(msg: Message, state: FSMContext):
    v = parse_positive_int(msg.text, 0, 1_000_000_000)
    if v is None:
        await msg.answer("❌ Raqam kiriting.")
        return
    data = await state.get_data()
    flt = data.get("search_filter", {})
    flt["min_price"] = v
    await state.update_data(search_filter=flt)
    await state.set_state(SearchStates.price_max)
    await msg.answer("💰 Maksimal narx (o'tkazib yuborish uchun -):",
                     reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                         [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="search_back")]
                     ]))


@router.message(StateFilter(SearchStates.price_max), F.text)
async def search_price_max(msg: Message, state: FSMContext):
    if msg.text.strip() == "-":
        pass
    else:
        v = parse_positive_int(msg.text, 0, 1_000_000_000)
        if v is None:
            await msg.answer("❌ Raqam kiriting yoki -")
            return
        data = await state.get_data()
        flt = data.get("search_filter", {})
        flt["max_price"] = v
        await state.update_data(search_filter=flt)
    await state.set_state(SearchStates.menu)
    await msg.answer("✅ Filtr saqlandi.", reply_markup=search_menu_kb())


@router.message(StateFilter(SearchStates.hero_min), F.text)
async def search_hero(msg: Message, state: FSMContext):
    v = parse_positive_int(msg.text, 0, 10000)
    if v is None:
        await msg.answer("❌ Raqam kiriting.")
        return
    data = await state.get_data()
    flt = data.get("search_filter", {})
    flt["min_hero"] = v
    await state.update_data(search_filter=flt)
    await state.set_state(SearchStates.menu)
    await msg.answer("✅ Saqlandi.", reply_markup=search_menu_kb())


@router.message(StateFilter(SearchStates.skin_min), F.text)
async def search_skin(msg: Message, state: FSMContext):
    v = parse_positive_int(msg.text, 0, 10000)
    if v is None:
        await msg.answer("❌ Raqam kiriting.")
        return
    data = await state.get_data()
    flt = data.get("search_filter", {})
    flt["min_skin"] = v
    await state.update_data(search_filter=flt)
    await state.set_state(SearchStates.menu)
    await msg.answer("✅ Saqlandi.", reply_markup=search_menu_kb())


@router.callback_query(F.data.startswith("scr:"), StateFilter(SearchStates.menu))
async def search_currank(cb: CallbackQuery, state: FSMContext):
    rank = cb.data.split(":", 1)[1]
    data = await state.get_data()
    flt = data.get("search_filter", {})
    flt["current_rank"] = rank
    await state.update_data(search_filter=flt)
    await safe_edit(cb, f"✅ Hozirgi rank: {rank}", reply_markup=search_menu_kb())
    await safe_answer(cb)


@router.callback_query(F.data.startswith("spr:"), StateFilter(SearchStates.menu))
async def search_peakrank(cb: CallbackQuery, state: FSMContext):
    rank = cb.data.split(":", 1)[1]
    data = await state.get_data()
    flt = data.get("search_filter", {})
    flt["peak_rank"] = rank
    await state.update_data(search_filter=flt)
    await safe_edit(cb, f"✅ Peak rank: {rank}", reply_markup=search_menu_kb())
    await safe_answer(cb)


@router.callback_query(F.data.startswith("link_toggle:"), StateFilter(SearchStates.menu))
async def search_link(cb: CallbackQuery, state: FSMContext):
    name = cb.data.split(":", 1)[1]
    data = await state.get_data()
    flt = data.get("search_filter", {})
    flt["link"] = name
    await state.update_data(search_filter=flt)
    await safe_edit(cb, f"✅ Link: {name}", reply_markup=search_menu_kb())
    await safe_answer(cb)


@router.callback_query(F.data.startswith("sort:"), StateFilter(SearchStates.menu))
async def search_sort(cb: CallbackQuery, state: FSMContext):
    s = cb.data.split(":", 1)[1]
    data = await state.get_data()
    flt = data.get("search_filter", {})
    flt["sort"] = s
    await state.update_data(search_filter=flt)
    listings = await listing_service.search_filtered(**flt, limit=20)
    await _render_results(cb, state, listings)
    await safe_answer(cb)


async def _render_results(cb: CallbackQuery, state: FSMContext, listings):
    if not listings:
        await safe_edit(cb, "🔎 Hech narsa topilmadi.", reply_markup=search_menu_kb())
        return
    await cb.message.answer(f"🔎 {len(listings)} ta natija:")
    for l in listings[:10]:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👀 Ko'rish", callback_data=f"view_listing:{l.id}")]
        ])
        await cb.message.answer(format_listing_card(l), reply_markup=kb)
    await state.set_state(SearchStates.menu)


@router.callback_query(F.data.startswith("view_listing:"))
async def view_listing(cb: CallbackQuery):
    lid = int(cb.data.split(":", 1)[1])
    l = await listing_service.get(lid)
    if not l or l.status != "ACTIVE":
        await safe_answer(cb, "E'lon mavjud emas", show_alert=True)
        return
    media = await listing_service.get_media(lid)
    from app.database.db import async_session
    from app.database.repository import UserRepo
    async with async_session() as session:
        owner = await UserRepo.get_by_id(session, l.user_id)
    from app.utils.formatters import format_listing_channel_text
    text = format_listing_channel_text(l, owner)
    kb_rows = []
    if owner and owner.username:
        kb_rows.append([InlineKeyboardButton(text="👤 Sotuvchi bilan bog'lanish",
                                              url=f"https://t.me/{owner.username}")])
    kb = InlineKeyboardMarkup(inline_keyboard=kb_rows) if kb_rows else None

    if not media:
        await cb.message.answer(text, reply_markup=kb)
    elif len(media) == 1 and media[0].type == "video":
        await cb.message.answer_video(media[0].telegram_file_id, caption=text, reply_markup=kb)
    elif len(media) == 1 and media[0].type == "photo":
        await cb.message.answer_photo(media[0].telegram_file_id, caption=text, reply_markup=kb)
    elif len(media) == 2:
        from aiogram.types import InputMediaPhoto
        group = [InputMediaPhoto(media=m.telegram_file_id, caption=text if i == 0 else "")
                 for i, m in enumerate(media)]
        await cb.message.answer_media_group(group)
        if kb:
            await cb.message.answer("⬇️", reply_markup=kb)
    await safe_answer(cb)