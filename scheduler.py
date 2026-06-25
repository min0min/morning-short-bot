from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz

from config import KST_TIMEZONE
from storage import load_state
from exchanges import get_bitget_price
from scanner import scan_latest_closed_15m_oc
from strategy import create_position, add_entry_if_needed, check_tp, check_sl_after_16, update_open_position_metrics
from messages import entry_message, add_message, close_message, scan_result_message

async def closed_15m_scan_job(bot, chat_id):
    """
    알림봇과 동일한 방식:
    09:15에 최근 마감 15분봉 O→C 기준으로 급등률 계산.
    """
    state = load_state()
    if not state.get("running"):
        return

    if state.get("open_position"):
        print("[JOB] closed 15m scan skipped: open position exists")
        return

    threshold = state["settings"]["pump_threshold_pct"]
    result = await scan_latest_closed_15m_oc(threshold)

    candidates = result["candidates"]
    signal = result["signal"]

    await bot.send_message(
        chat_id=chat_id,
        text=scan_result_message(
            candidates,
            threshold,
            signal=signal,
            total_symbols=result["total_symbols"],
            errors=result["errors"],
            title=f"{result['target_open']} 마감 15분봉 SCAN"
        )
    )

    if not signal:
        return

    pos = create_position(signal, reason="CLOSED_15M_OC_TOP1")
    await bot.send_message(chat_id=chat_id, text=entry_message(pos, signal))

async def position_watch_job(bot, chat_id):
    state = load_state()
    if not state.get("running"):
        return

    pos = state.get("open_position")
    if not pos:
        return

    price = await get_bitget_price(pos["symbol"])

    update_open_position_metrics(price)

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

    # 매일 09:15, 방금 마감된 09:00~09:15 15분봉으로 판단
    scheduler.add_job(closed_15m_scan_job, "cron", hour=9, minute=15, args=[app.bot, chat_id])

    # 오픈 포지션 감시
    scheduler.add_job(position_watch_job, "interval", seconds=30, args=[app.bot, chat_id])

    # 16시 손절 체크
    scheduler.add_job(sl_check_job, "cron", hour=16, minute=0, args=[app.bot, chat_id])

    scheduler.start()
    return scheduler
