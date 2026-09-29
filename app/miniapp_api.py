import hashlib
import hmac
import json
import random
import time
from datetime import datetime, timedelta
from urllib.parse import parse_qsl

from aiohttp import web
from sqlalchemy import select, text

from app.config import config
from app.database.db import async_session
from app.database.models import User, Listing, ListingMedia, Admin, Setting, MarketplaceOrder
from app.services.balance_service import balance_service
from app.services.transaction_service import transaction_service
from app.services.user_service import user_service

MAX_AUTH_AGE = 86400
ORIGIN = "https://mlbb-market.floot.app"


def _init_user(raw: str) -> dict:
    if not raw:
        raise web.HTTPUnauthorized(text="Telegram authorization required")
    data = dict(parse_qsl(raw, keep_blank_values=True))
    received = data.pop("hash", "")
    auth_date = int(data.get("auth_date", "0") or 0)
    if not received or not auth_date or abs(int(time.time()) - auth_date) > MAX_AUTH_AGE:
        raise web.HTTPUnauthorized(text="Invalid or expired Telegram session")
    check = "\n".join(f"{k}={data[k]}" for k in sorted(data))
    secret = hmac.new(b"WebAppData", config.bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received):
        raise web.HTTPUnauthorized(text="Invalid Telegram signature")
    return json.loads(data.get("user", "{}"))


def _raw(request):
    auth = request.headers.get("Authorization", "")
    return auth[4:] if auth.startswith("tma ") else request.headers.get("X-Telegram-Init-Data", "")


async def user(request):
    tg = _init_user(_raw(request))
    async with async_session() as s:
        u = await s.scalar(select(User).where(User.telegram_id == int(tg["id"])))
        if not u:
            raise web.HTTPNotFound(text="User not found")
        admin = int(tg["id"]) in config.super_admin_ids or await s.scalar(select(Admin).where(Admin.telegram_id == int(tg["id"])))
        return _json(request, {"user":{"id":u.telegram_id,"username":u.username,"name":u.first_name,"balance":u.balance or 0,"diamonds":u.diamonds or 0,"coins":u.game_coins or 0,"vr":u.vr_balance or 0,"admin":bool(admin)}})


async def listings(request):
    q = request.query.get("q", "").lower().strip()
    now = datetime.utcnow()
    async with async_session() as s:
        rows = (await s.execute(
            select(Listing, User)
            .join(User, User.id == Listing.user_id)
            .where(Listing.status == "ACTIVE", Listing.marketplace_enabled.is_(True))
            .order_by(Listing.is_top.desc(), Listing.created_at.desc()).limit(100)
        )).all()
        out=[]
        for l,u in rows:
            hay=f"{l.current_rank} {l.peak_rank} {l.hero_count} {l.skin_count} {l.description or ''} {u.username or ''}".lower()
            if q and q not in hay: continue
            media=(await s.execute(select(ListingMedia).where(ListingMedia.listing_id==l.id))).scalars().all()
            promo = l.promo_level if l.promo_until and l.promo_until > now else "NONE"
            out.append({"id":l.id,"title":f"{l.current_rank} • {l.hero_count} hero • {l.skin_count} skin",
                        "category":"Account","price":l.price,"vrPrice":l.marketplace_vr_price or max(1,(int(l.price)+19)//20),
                        "seller":u.username or u.first_name or "Seller","ownerId":u.telegram_id,"badge":promo if promo!="NONE" else ("TOP" if l.is_top else "Marketplace"),
                        "promo":promo,"rank":l.current_rank,"peakRank":l.peak_rank,"heroCount":l.hero_count,"skinCount":l.skin_count,
                        "links":[x for x in (l.account_links or "").split(",") if x],"description":l.description or "","mediaCount":len(media)})
        return _json(request, {"items":out})


async def buy_vr(request):
    tg=_init_user(_raw(request)); body=await request.json()
    amount_vr=int(body.get("amountVr",0)); rate=await _setting_int("vr_som_rate",20)
    if amount_vr < 50 or amount_vr > 100000 or amount_vr % 50 != 0:
        raise web.HTTPBadRequest(text="VR miqdori 50 dan boshlanadi va 50 ga karrali bo'lishi kerak")
    cost=amount_vr*rate; tg_id=int(tg["id"])
    if not await balance_service.atomic_debit(tg_id,cost):
        raise web.HTTPBadRequest(text="So'm balans yetarli emas")
    async with async_session() as s:
        u=await s.scalar(select(User).where(User.telegram_id==tg_id))
        if not u:
            await balance_service.atomic_credit(tg_id,cost); raise web.HTTPBadRequest(text="User not found")
        u.vr_balance=(u.vr_balance or 0)+amount_vr
        await s.commit()
    u2=await user_service.get_by_tg(tg_id)
    await transaction_service.create(user_id=u2.id,amount=-cost,ttype="vr_purchase",
                                     description=f"{amount_vr} VR sotib olindi")
    return _json(request,{"ok":True,"vr":amount_vr,"cost":cost})


async def ads(request):
    async with async_session() as s:
        rows=(await s.execute(text("SELECT id,title,description,target_url,active FROM marketplace_ads WHERE active=TRUE ORDER BY id DESC"))).mappings().all()
    return _json(request,{"items":[dict(x) for x in rows]})


async def promote_listing(request):
    tg=_init_user(_raw(request)); body=await request.json()
    lid=int(body.get("listingId",0)); tier=str(body.get("tier","TOP")).upper(); tg_id=int(tg["id"])
    setting={"TOP":"promo_top_vr","VIP":"promo_vip_vr","ULTRA":"promo_ultra_vr"}.get(tier)
    if not setting: raise web.HTTPBadRequest(text="Noto'g'ri promo")
    cost=await _setting_int(setting,{"TOP":50,"VIP":100,"ULTRA":200}[tier])
    hours={"TOP":24,"VIP":72,"ULTRA":168}[tier]
    async with async_session() as s:
        u=await s.scalar(select(User).where(User.telegram_id==tg_id))
        l=await s.get(Listing,lid)
        if not u or not l or l.user_id != u.id: raise web.HTTPForbidden(text="Bu e'lon sizniki emas")
        if l.status!="ACTIVE" or not l.marketplace_enabled: raise web.HTTPBadRequest(text="E'lon Marketplace'da faol emas")
        if (u.vr_balance or 0)<cost: raise web.HTTPBadRequest(text="VR yetarli emas")
        u.vr_balance-=cost; l.promo_level=tier; l.promo_until=datetime.utcnow()+timedelta(hours=hours); l.is_top=True
        await s.commit()
    return _json(request,{"ok":True,"tier":tier,"cost":cost,"hours":hours})


async def orders(request):
    tg=_init_user(_raw(request)); tg_id=int(tg["id"])
    async with async_session() as s:
        u=await s.scalar(select(User).where(User.telegram_id==tg_id))
        if not u: raise web.HTTPNotFound(text="User not found")
        rows=(await s.execute(select(MarketplaceOrder,Listing).join(Listing,Listing.id==MarketplaceOrder.listing_id)
                              .where((MarketplaceOrder.buyer_id==u.id)|(MarketplaceOrder.seller_id==u.id))
                              .order_by(MarketplaceOrder.created_at.desc()).limit(50))).all()
        return _json(request,{"items":[{"id:o.id,"listingId:o.listing_id,"priceVr":o.price_vr,"status":o.status,
                                       "role":"BUYER" if o.buyer_id==u.id else "SELLER","title":f"{l.current_rank} • {l.hero_count} hero • {l.skin_count} skin"}
                                      for o,l in rows]})


async def buy_listing(request):
    tg=_init_user(_raw(request)); body=await request.json(); lid=int(body.get("listingId",0)); tg_id=int(tg["id"])
    async with async_session() as s:
        buyer=await s.scalar(select(User).where(User.telegram_id==tg_id))
        l=await s.get(Listing,lid)
        if not buyer or not l: raise web.HTTPNotFound(text="E'lon topilmadi")
        seller=await s.get(User,l.user_id)
        if not seller or seller.id==buyer.id: raise web.HTTPBadRequest(text="O'zingizning e'loningizni sotib olib bo'lmaydi")
        if l.status!="ACTIVE" or not l.marketplace_enabled: raise web.HTTPBadRequest(text="E'lon faol emas")
        existing=await s.scalar(select(MarketplaceOrder).where(MarketplaceOrder.listing_id==lid,MarketplaceOrder.status=="PENDING"))
        if existing: raise web.HTTPBadRequest(text="Bu e'lon bo'yicha allaqachon buyurtma bor")
        price=int(l.marketplace_vr_price or max(1,(int(l.price)+19)//20))
        if (buyer.vr_balance or 0)<price: raise web.HTTPBadRequest(text=f"VR yetarli emas: {price} VR kerak")
        buyer.vr_balance-=price
        o=MarketplaceOrder(listing_id=lid,buyer_id=buyer.id,seller_id=seller.id,price_vr=price,status="PENDING")
        s.add(o); await s.commit(); await s.refresh(o)
        return _json(request,{"ok":True,"orderId":o.id,"priceVr":price,"status":"PENDING"})


async def confirm_order(request):
    tg=_init_user(_raw(request)); oid=int(request.match_info["id"]); tg_id=int(tg["id"])
    async with async_session() as s:
        seller=await s.scalar(select(User).where(User.telegram_id==tg_id))
        o=await s.get(MarketplaceOrder,oid)
        if not seller or not o or o.seller_id!=seller.id: raise web.HTTPForbidden(text="Faqat sotuvchi tasdiqlashi mumkin")
        if o.status!="PENDING": raise web.HTTPBadRequest(text="Buyurtma faol emas")
        l=await s.get(Listing,o.listing_id); buyer=await s.get(User,o.buyer_id)
        if not l or not buyer: raise web.HTTPBadRequest(text="Buyurtma ma'lumoti topilmadi")
        seller.vr_balance=(seller.vr_balance or 0)+o.price_vr
        o.status="COMPLETED"; o.confirmed_at=datetime.utcnow(); l.status="SOLD"; l.marketplace_enabled=False; l.sold_at=datetime.utcnow()
        await s.commit()
    return _json(request,{"ok":True,"status":"COMPLETED"})


async def cancel_order(request):
    tg=_init_user(_raw(request)); oid=int(request.match_info["id"]); tg_id=int(tg["id"])
    async with async_session() as s:
        u=await s.scalar(select(User).where(User.telegram_id==tg_id)); o=await s.get(MarketplaceOrder,oid)
        if not u or not o or (o.buyer_id!=u.id and o.seller_id!=u.id): raise web.HTTPForbidden(text="Ruxsat yo'q")
        if o.status!="PENDING": raise web.HTTPBadRequest(text="Buyurtma faol emas")
        buyer=await s.get(User,o.buyer_id); buyer.vr_balance=(buyer.vr_balance or 0)+o.price_vr; o.status="CANCELLED"
        await s.commit()
    return _json(request,{"ok":True,"status":"CANCELLED"})


async def _setting_int(key, default):
    async with async_session() as s:
        v=await s.scalar(select(Setting).where(Setting.key==key))
        try: return int(v.value) if v else default
        except Exception: return default


async def packages(request):
    async with async_session() as s:
        rows=(await s.execute(text("SELECT id, diamonds, bonus, price, active FROM diamond_packages WHERE active=TRUE ORDER BY price"))).mappings().all()
    return _json(request, {"items":[dict(x) for x in rows]})


async def buy_diamonds(request):
    tg=_init_user(_raw(request)); body=await request.json(); pid=int(body.get("packageId",0)); tg_id=int(tg["id"])
    async with async_session() as s:
        p=(await s.execute(text("SELECT id, diamonds, bonus, price FROM diamond_packages WHERE id=:id AND active=TRUE"),{"id":pid})).mappings().first()
    if not p: raise web.HTTPNotFound(text="Package not found")
    if not await balance_service.atomic_debit(tg_id,int(p["price"])): raise web.HTTPBadRequest(text="Balans yetarli emas")
    async with async_session() as s:
        u=await s.scalar(select(User).where(User.telegram_id==tg_id))
        if not u:
            await balance_service.atomic_credit(tg_id,int(p["price"])); raise web.HTTPBadRequest(text="User not found")
        added=int(p["diamonds"])+int(p["bonus"] or 0); u.diamonds=(u.diamonds or 0)+added; await s.commit()
    u=await user_service.get_by_tg(tg_id)
    await transaction_service.create(user_id=u.id,amount=-int(p["price"]),ttype="diamond_purchase",description=f"Diamond package #{pid}")
    return _json(request, {"ok":True,"added":added})


async def game(request):
    tg=_init_user(_raw(request)); body=await request.json(); name=str(body.get("game","coin_flip")); stake=max(1,min(int(body.get("stake",25)),1000)); tg_id=int(tg["id"])
    async with async_session() as s:
        u=await s.scalar(select(User).where(User.telegram_id==tg_id))
        if not u or (u.game_coins or 0)<stake: raise web.HTTPBadRequest(text="Coin yetarli emas")
        u.game_coins-=stake; r=random.random()
        if name=="coin_flip": reward=stake*2 if r<.47 else 0; result="WIN" if reward else "LOSE"
        elif name=="dice": n=random.randint(1,6); reward=stake*3 if n>=5 else 0; result=f"Dice: {n}"
        elif name=="wheel": reward=random.choice([0,stake,stake*2,stake*3,stake*5]); result=f"Wheel: +{reward}"
        elif name=="mines": reward=stake*2 if r<.42 else 0; result="SAFE" if reward else "MINE"
        else: raise web.HTTPBadRequest(text="Unknown game")
        u.game_coins+=reward
        await s.execute(text("INSERT INTO game_events (user_id, game, stake, reward) VALUES (:u,:g,:s,:r)"),{"u":tg_id,"g":name,"s":stake,"r":reward})
        await s.commit()
        return _json(request, {"ok":True,"result":result,"reward":reward,"coins":u.game_coins})


async def admin(request):
    tg=_init_user(_raw(request)); tg_id=int(tg["id"])
    async with async_session() as s:
        ok=tg_id in config.super_admin_ids or await s.scalar(select(Admin).where(Admin.telegram_id==tg_id))
        if not ok: raise web.HTTPForbidden(text="Admin only")
        users=await s.scalar(text("SELECT count(*) FROM users"))
        active=await s.scalar(text("SELECT count(*) FROM listings WHERE status='ACTIVE'"))
        packages=(await s.execute(text("SELECT id,diamonds,bonus,price,active FROM diamond_packages ORDER BY price"))).mappings().all()
        ads=(await s.execute(text("SELECT id,title,description,target_url,active FROM marketplace_ads ORDER BY id DESC"))).mappings().all()
        settings={x.key:x.value for x in (await s.execute(select(Setting))).scalars().all()}
        return _json(request,{"stats":{"users":users,"activeListings":active},"packages":[dict(x) for x in packages],"ads":[dict(x) for x in ads],"settings":settings})


async def admin_package(request):
    tg=_init_user(_raw(request)); body=await request.json(); await _check_admin(tg)
    async with async_session() as s:
        if body.get("id"):
            await s.execute(text("UPDATE diamond_packages SET diamonds=:d,bonus=:b,price=:p,active=:a WHERE id=:id"),{"d":int(body["diamonds"]),"b":int(body.get("bonus",0)),"p":int(body["price"]),"a":bool(body.get("active",True)),"id":int(body["id"])})
        else:
            await s.execute(text("INSERT INTO diamond_packages (diamonds,bonus,price,active) VALUES (:d,:b,:p,:a)"),{"d":int(body["diamonds"]),"b":int(body.get("bonus",0)),"p":int(body["price"]),"a":bool(body.get("active",True))})
        await s.commit()
    return _json(request,{"ok":True})


async def admin_package_delete(request):
    tg=_init_user(_raw(request)); await _check_admin(tg); pid=int(request.match_info["id"])
    async with async_session() as s:
        await s.execute(text("UPDATE diamond_packages SET active=FALSE WHERE id=:id"),{"id":pid}); await s.commit()
    return _json(request,{"ok":True})


async def admin_listing(request):
    tg=_init_user(_raw(request)); await _check_admin(tg); lid=int(request.match_info["id"]); body=await request.json()
    async with async_session() as s:
        l=await s.get(Listing,lid)
        if not l: raise web.HTTPNotFound(text="Listing not found")
        if "marketplace" in body: l.marketplace_enabled=bool(body["marketplace"])
        if "status" in body: l.status=str(body["status"])
        if "top" in body: l.is_top=bool(body["top"])
        await s.commit()
    return _json(request,{"ok":True})


async def admin_listings(request):
    tg=_init_user(_raw(request)); await _check_admin(tg)
    async with async_session() as s:
        rows=(await s.execute(
            select(Listing, User).join(User, User.id==Listing.user_id)
            .order_by(Listing.created_at.desc()).limit(100)
        )).all()
        return _json(request,{"items":[
            {"id":l.id,"title":f"{l.current_rank} • {l.hero_count} hero • {l.skin_count} skin","price":l.price,
             "seller":u.username or u.first_name or str(u.telegram_id),"status":l.status,
             "marketplace":bool(l.marketplace_enabled),"top":bool(l.is_top)}
            for l,u in rows
        ]})


async def admin_setting(request):
    tg=_init_user(_raw(request)); await _check_admin(tg); body=await request.json()
    key=str(body.get("key","")).strip()
    value=str(body.get("value","")).strip()
    if not key or len(key)>64: raise web.HTTPBadRequest(text="Invalid setting")
    async with async_session() as s:
        setting=await s.get(Setting,key)
        if setting: setting.value=value
        else: s.add(Setting(key=key,value=value))
        await s.commit()
    return _json(request,{"ok":True})


async def admin_ad(request):
    tg=_init_user(_raw(request)); await _check_admin(tg); body=await request.json()
    async with async_session() as s:
        if body.get("id"):
            await s.execute(text("UPDATE marketplace_ads SET title=:t,description=:d,target_url=:u,active=:a WHERE id=:id"),
                            {"t":body["title"],"d":body.get("description",""),"u":body.get("targetUrl"),"a":bool(body.get("active",True)),"id":int(body["id"])})
        else:
            await s.execute(text("INSERT INTO marketplace_ads (title,description,target_url,active) VALUES (:t,:d,:u,:a)"),
                            {"t":body["title"],"d":body.get("description",""),"u":body.get("targetUrl"),"a":bool(body.get("active",True))})
        await s.commit()
    return _json(request,{"ok":True})


async def _check_admin(tg):
    tg_id=int(tg["id"])
    if tg_id in config.super_admin_ids: return True
    async with async_session() as s:
        if await s.scalar(select(Admin).where(Admin.telegram_id==tg_id)): return True
    raise web.HTTPForbidden(text="Admin only")


def _json(request,data,status=200):
    r=web.json_response(data,status=status)
    if request.headers.get("Origin")==ORIGIN: r.headers["Access-Control-Allow-Origin"]=ORIGIN
    r.headers["Access-Control-Allow-Headers"]="Content-Type, Authorization, X-Telegram-Init-Data"
    r.headers["Access-Control-Allow-Methods"]="GET, POST, PATCH, DELETE, OPTIONS"
    return r


@web.middleware
async def cors(request, handler):
    if request.method=="OPTIONS": return _json(request,{})
    return await handler(request)


def register_miniapp_routes(app):
    app.middlewares.append(cors)
    app.router.add_get("/miniapp/me",user)
    app.router.add_get("/miniapp/listings",listings)
    app.router.add_get("/miniapp/packages",packages)
    app.router.add_get("/miniapp/ads",ads)
    app.router.add_post("/miniapp/buy-vr",buy_vr)
    app.router.add_post("/miniapp/promote",promote_listing)
    app.router.add_get("/miniapp/orders",orders)
    app.router.add_post("/miniapp/buy-listing",buy_listing)
    app.router.add_post("/miniapp/orders/{id}/confirm",confirm_order)
    app.router.add_post("/miniapp/orders/{id}/cancel",cancel_order)
    app.router.add_post("/miniapp/purchase-diamonds",buy_diamonds)
    app.router.add_post("/miniapp/game",game)
    app.router.add_get("/miniapp/admin",admin)
    app.router.add_get("/miniapp/admin/listings",admin_listings)
    app.router.add_post("/miniapp/admin/settings",admin_setting)
    app.router.add_post("/miniapp/admin/ads",admin_ad)
    app.router.add_post("/miniapp/admin/packages",admin_package)
    app.router.add_delete("/miniapp/admin/packages/{id}",admin_package_delete)
    app.router.add_patch("/miniapp/admin/listings/{id}",admin_listing)
