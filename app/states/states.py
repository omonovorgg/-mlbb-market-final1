from aiogram.fsm.state import State, StatesGroup
class ListingCreate(StatesGroup):
    deal_type=State(); current_rank=State(); peak_rank=State(); hero_count=State(); skin_count=State()
    win_rate=State(); main_hero=State(); collection_value=State()
    account_links=State(); media=State(); price=State(); description=State(); preview=State()
class EditListing(StatesGroup):
    choosing_field=State(); new_value=State(); confirm_paid=State()
class SearchStates(StatesGroup):
    menu=State(); price_min=State(); price_max=State(); hero_min=State(); skin_min=State()
class BalanceStates(StatesGroup):
    entering_amount=State(); waiting_receipt=State(); entering_promo=State()
class CardStates(StatesGroup):
    add_number=State(); add_holder=State(); add_bank=State(); edit_card=State()
class AdminStates(StatesGroup):
    user_search=State(); user_message=State(); user_balance_amount=State(); user_balance_reason=State(); broadcast_message=State(); broadcast_confirm=State(); pricing_edit=State(); listing_search=State(); channel_test=State(); promo_create_code=State(); promo_create_amount=State(); promo_create_limit=State(); promo_create_expire=State(); settings_edit=State(); report_note=State(); giveaway_video=State(); giveaway_text=State(); giveaway_confirm=State()
