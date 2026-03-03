import os, asyncio
from datetime import datetime
from typing import Any, Dict, Optional, List

from fastapi import FastAPI, Request, HTTPException
from sqlmodel import select

from .db import init_db, get_session
from .models import Family, Member, AlertEvent
from .telegram_client import send_message, inline_keyboard, answer_callback_query
from .alert_listener import fetch_alerts, extract_alert_items, AlertStateMachine
from .ui import admin_page

POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "2"))
ALL_CLEAR_AFTER_SECONDS = int(os.getenv("ALL_CLEAR_AFTER_SECONDS", "600"))
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "")
ADMIN_TELEGRAM_CHAT_ID = os.getenv("ADMIN_TELEGRAM_CHAT_ID")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

app = FastAPI(title="Red Alert → Telegram Check-in (MVP + UI)")
sm = AlertStateMachine(all_clear_after_seconds=ALL_CLEAR_AFTER_SECONDS)

def require_admin(token: str):
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=500, detail="ADMIN_TOKEN is not set on the server")
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

def get_or_create_family(code: str) -> Family:
    with get_session() as s:
        fam = s.exec(select(Family).where(Family.code == code)).first()
        if fam:
            return fam
        fam = Family(code=code)
        s.add(fam)
        s.commit()
        s.refresh(fam)
        return fam

def upsert_member(family_id: int, telegram_user_id: int, telegram_chat_id: int, display_name: str) -> Member:
    with get_session() as s:
        m = s.exec(select(Member).where(Member.family_id == family_id, Member.telegram_user_id == telegram_user_id)).first()
        if m:
            m.telegram_chat_id = telegram_chat_id
            m.display_name = display_name
            m.updated_at = datetime.utcnow()
            s.add(m); s.commit(); s.refresh(m)
            return m
        m = Member(family_id=family_id, telegram_user_id=telegram_user_id, telegram_chat_id=telegram_chat_id, display_name=display_name)
        s.add(m); s.commit(); s.refresh(m)
        return m

def current_active_event() -> Optional[AlertEvent]:
    with get_session() as s:
        return s.exec(select(AlertEvent).where(AlertEvent.is_active == True)).first()

def start_event() -> AlertEvent:
    with get_session() as s:
        ev = AlertEvent(is_active=True, started_at=datetime.utcnow(), last_alert_at=datetime.utcnow(), scope="GLOBAL")
        s.add(ev); s.commit(); s.refresh(ev)
        return ev

def touch_event(ev_id: int):
    with get_session() as s:
        ev = s.get(AlertEvent, ev_id)
        if not ev: return
        ev.last_alert_at = datetime.utcnow()
        s.add(ev); s.commit()

def clear_event(ev_id: int):
    with get_session() as s:
        ev = s.get(AlertEvent, ev_id)
        if not ev: return
        ev.is_active = False
        ev.cleared_at = datetime.utcnow()
        s.add(ev); s.commit()

def list_members() -> List[Member]:
    with get_session() as s:
        return list(s.exec(select(Member)).all())

def list_events(limit: int = 25) -> List[AlertEvent]:
    with get_session() as s:
        return list(s.exec(select(AlertEvent).order_by(AlertEvent.id.desc()).limit(limit)).all())

def set_member_status(member_id: int, status: str, event_id: int):
    with get_session() as s:
        m = s.get(Member, member_id)
        if not m: return
        m.last_status = status
        m.last_checkin_event_id = event_id
        m.updated_at = datetime.utcnow()
        s.add(m); s.commit()

def build_checkin_keyboard(event_id: int) -> Dict[str, Any]:
    return inline_keyboard([[{"text":"✅ I'm OK","callback_data":f"ok:{event_id}"},{"text":"❗ Need help","callback_data":f"help:{event_id}"}]])

async def send_checkins(event_id: int):
    members = list_members()
    if not members: return
    text = "🚨 All clear.\nPlease confirm you're OK:"
    kb = build_checkin_keyboard(event_id)
    for m in members:
        try:
            send_message(m.telegram_chat_id, text, reply_markup=kb)
            set_member_status(m.id, "UNKNOWN", event_id)
        except Exception:
            pass
    if ADMIN_TELEGRAM_CHAT_ID:
        try:
            send_message(int(ADMIN_TELEGRAM_CHAT_ID), f"Sent check-in to {len(members)} members for event #{event_id}.")
        except Exception:
            pass

async def poll_loop():
    await asyncio.sleep(2)
    while True:
        payload, err = fetch_alerts()
        alerts = extract_alert_items(payload) if payload else []
        actions = sm.ingest(alerts)
        ev = current_active_event()
        if actions["became_active"]:
            ev = ev or start_event()
            touch_event(ev.id)
        elif actions["new_alert"] and ev:
            touch_event(ev.id)
        if actions["became_cleared"] and ev:
            clear_event(ev.id)
            await send_checkins(ev.id)
        await asyncio.sleep(POLL_INTERVAL_SECONDS)

@app.on_event("startup")
async def _startup():
    init_db()
    asyncio.create_task(poll_loop())

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/admin")
def admin(token: str):
    require_admin(token)
    members = [{"display_name":m.display_name,"last_status":m.last_status,"last_checkin_event_id":m.last_checkin_event_id,"updated_at":m.updated_at} for m in list_members()]
    events = [{"id":e.id,"started_at":e.started_at,"last_alert_at":e.last_alert_at,"cleared_at":e.cleared_at,"is_active":e.is_active} for e in list_events()]
    return admin_page(members, events, base_url=PUBLIC_BASE_URL or "", token=token)

@app.post("/admin/send_test_checkin")
async def send_test_checkin(token: str):
    require_admin(token)
    ev = start_event()
    clear_event(ev.id)
    await send_checkins(ev.id)
    return {"ok": True, "event_id": ev.id}

@app.post("/telegram/webhook")
async def telegram_webhook(req: Request):
    update: Dict[str, Any] = await req.json()

    if "message" in update and update["message"].get("text","").startswith("/start"):
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        user = msg.get("from", {})
        user_id = user.get("id")
        name = " ".join([user.get("first_name",""), user.get("last_name","")]).strip() or user.get("username","User")
        parts = msg.get("text","").split()
        family_code = parts[1] if len(parts) > 1 else "DEFAULT"
        fam = get_or_create_family(family_code)
        upsert_member(fam.id, user_id, chat_id, name)
        send_message(chat_id, f"✅ You're added to family '{family_code}'.\nYou'll get a check-in after an all-clear.")
        return {"ok": True}

    if "callback_query" in update:
        cq = update["callback_query"]
        data = cq.get("data","")
        cq_id = cq.get("id")
        user_id = cq.get("from", {}).get("id")
        action, _, evs = data.partition(":")
        try:
            event_id = int(evs)
        except Exception:
            event_id = None
        with get_session() as s:
            member = s.exec(select(Member).where(Member.telegram_user_id == user_id)).first()
        if member and event_id:
            if action == "ok":
                set_member_status(member.id, "OK", event_id)
                answer_callback_query(cq_id, "Got it ❤️ Stay safe.")
            elif action == "help":
                set_member_status(member.id, "HELP", event_id)
                answer_callback_query(cq_id, "Noted. Someone will reach out now.", show_alert=True)
                if ADMIN_TELEGRAM_CHAT_ID:
                    try:
                        send_message(int(ADMIN_TELEGRAM_CHAT_ID), f"❗ {member.display_name} pressed NEED HELP (event #{event_id}).")
                    except Exception:
                        pass
            else:
                answer_callback_query(cq_id, "Unknown action.")
        else:
            answer_callback_query(cq_id, "You're not registered yet. Send /start FAMILYCODE")
        return {"ok": True}

    return {"ok": True}
