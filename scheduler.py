from datetime import datetime
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import KST_TIMEZONE
from storage import load_state
from exchanges import scan_top_pump_crosslisted, get_bitget_price
from strategy import create_position, add_entry_if_needed, check_tp, check_sl_after_16
from messages import entry_message, add_message, close_message

async def morning_scan_job(bot, chat_id):
    state = load_state()
    if not state.get("running"):
        return
    if state.get("open_position"):
        return

    threshold = state["settings"]["pump_threshold_pct"]
    signal, candidates = await scan_top_pump_crosslisted(threshold)

    if not signal:
        await bot.send_message(chat_id=chat_id, text="📭 [09:15 PAPER SCAN]\n\n조건 충족 종목 없음")
        return

    pos = create_position(signal)
    await bot.send_message(chat_id=chat_id, text=entry_message(pos, signal))

async def position_watch_job(bot, chat_id):
    state = load_state()
    if not state.get("running"):
        return
    pos = state.get("open_position")
    if not pos:
        return

    price = await get_bitget_price(pos["symbol"])

    added = add_entry_if_needed(price)
    if added:
        entry, new_pos = added
        await bot.send_message(chat_id=chat_id, text=add_message(entry, new_pos))

    closed = check_tp(price)
    if closed:
        closed_pos, balance = closed
        await bot.send_message(chat_id=chat_id, text=close_message(closed_pos, balance))

async def sl_check_job(bot, chat_id):
    state = load_state()
    if not state.get("running"):
        return
    pos = state.get("open_position")
    if not pos:
        return

    price = await get_bitget_price(pos["symbol"])
    closed = check_sl_after_16(price)
    if closed:
        closed_pos, balance = closed
        await bot.send_message(chat_id=chat_id, text=close_message(closed_pos, balance))
    else:
        await bot.send_message(chat_id=chat_id, text="🕓 [16:00 SL CHECK]\n\n-30% 이하 손실 아님 → 홀딩 유지")

def setup_scheduler(app, chat_id):
    scheduler = AsyncIOScheduler(timezone=pytz.timezone(KST_TIMEZONE))

    scheduler.add_job(morning_scan_job, "cron", hour=9, minute=15, args=[app.bot, chat_id])
    scheduler.add_job(position_watch_job, "interval", seconds=30, args=[app.bot, chat_id])
    scheduler.add_job(sl_check_job, "cron", hour=16, minute=0, args=[app.bot, chat_id])

    scheduler.start()
    return scheduler
