import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv
load_dotenv()
def _split_ids(raw: str) -> List[int]: return [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]
def _normalize_db_url(raw: str) -> str:
    raw=(raw or "").strip()
    if raw.startswith("postgres://"): return "postgresql+asyncpg://"+raw[11:]
    if raw.startswith("postgresql://"): return "postgresql+asyncpg://"+raw[13:]
    return raw
@dataclass
class Config:
    bot_token:str=os.getenv("BOT_TOKEN","")
    super_admin_ids:List[int]=field(default_factory=lambda:_split_ids(os.getenv("SUPER_ADMIN_IDS","")))
    channel_id:int=int(os.getenv("CHANNEL_ID","0") or 0)
    channel_username:str=os.getenv("CHANNEL_USERNAME","")
    support_username:str=os.getenv("SUPPORT_USERNAME","@support")
    db_url:str=_normalize_db_url(os.getenv("DATABASE_URL") or os.getenv("DB_URL",""))
    port:int=int(os.getenv("PORT","8080"))
    webhook_url:str=os.getenv("WEBHOOK_URL","")
    deposit_auto_confirm_minutes:int=int(os.getenv("DEPOSIT_AUTO_CONFIRM_MINUTES","30") or 30)
config=Config()
DEFAULT_SETTINGS={"listing_create_price":"2000","listing_edit_price":"2000","price_change_price":"2000","free_edit_count":"1","free_price_change_count":"1","support_username":config.support_username,"channel_id":str(config.channel_id),"channel_username":config.channel_username,"listing_expiration_days":"30","maintenance_mode":"0","top_price":"10000"}
RANK_OPTIONS=["Warrior","Elite","Master","Grandmaster","Epic","Legend","Mythic","Mythical Honor","Mythical Glory","Mythical Immortal"]
LINK_OPTIONS=["Moonton","Google","Facebook","TikTok","Apple","VK"]
TRANSACTION_TYPES=["deposit","listing_create","listing_edit","price_change","top_purchase","bonus","admin_adjustment","refund"]
