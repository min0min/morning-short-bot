from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz

from config import KST_TIMEZONE
from storage import load_state, save_baseline, load_baseline
from exchanges import get_crosslisted_futures_snapshot, scan_top_15min_pump_crosslisted, get_bitget_price
from strategy import create_position, add_entry_if_needed, check_tp, check_sl_after_16
from messages import entry_message, add_message, close_message

async def baseline_0900_job(bot, chat_id):
    state = load_state()
    if not state.get("running"):
        return

    snapshot = await get_crosslisted_futures_snapshot()
    save_baseline(snapshot)

    await bot.send_message(
        chat_id=chat_id,
        text=f"🕘 [09:00 BASELINE 저장]\n\n교차상장 + 비트겟 선물 가능 종목 {len(snapshot)}개 기준가 저장 완료\n\n09:15에 15분 급등률 1등 종목만 선정합니다."
    )

async def morning_scan_job(bot, chat_id):
    state = load_state()
    if not state.get("running"):
        return
    if state.get("open_position"):
        return

    baseline_payload = load_baseline()
    if not baseline_payload:
        await bot.send_message(
            chat_id=chat_id,
            text="⚠️ [09:15 PAPER SCAN 실패]\n\n09:00 기준가 데이터가 없습니다.\n내일 09:00 기준가 저장 후 다시 스캔합니다."
        )
        return

    baseline_snapshot = baseline_payload.get("snapshot", {})
    threshold = state["settings"]["pump_threshold_pct"]

    signal, candidates = await scan_top_15min_pump_crosslisted(baseline_snapshot, threshold)

    if not signal:
        await bot.send_message(
            chat_id=chat_id,
            text=f"📭 [09:15 PAPER SCAN]\n\n09:00 → 09:15 기준\n+{threshold}% 이상 급등 종목 없음"
        )
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

    # 09:00 기준가 저장 → 09:15 급등률 계산
    scheduler.add_job(baseline_0900_job, "cron", hour=9, minute=0, args=[app.bot, chat_id])
    scheduler.add_job(morning_scan_job, "cron", hour=9, minute=15, args=[app.bot, chat_id])

    # 오픈 포지션 감시
    scheduler.add_job(position_watch_job, "interval", seconds=30, args=[app.bot, chat_id])

    # 16시 손절 체크
    scheduler.add_job(sl_check_job, "cron", hour=16, minute=0, args=[app.bot, chat_id])

    scheduler.start()
    return scheduler
