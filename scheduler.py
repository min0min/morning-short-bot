from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz

from config import KST_TIMEZONE
from storage import load_state, save_baseline, reset_window, update_window_with_snapshot, get_peak_candidates
from exchanges import get_crosslisted_futures_snapshot, get_bitget_price
from strategy import create_position, add_entry_if_needed, check_tp, check_sl_after_16
from messages import entry_message, add_message, close_message, scan_result_message

async def baseline_0900_job(bot, chat_id):
    state = load_state()
    if not state.get("running"):
        return

    print("[JOB] 09:00 baseline start")
    snapshot = await get_crosslisted_futures_snapshot()
    save_baseline(snapshot)
    reset_window(snapshot)

    print(f"[JOB] 09:00 baseline saved: {len(snapshot)} symbols")
    await bot.send_message(
        chat_id=chat_id,
        text=f"🕘 [09:00 BASELINE 저장]\n\n교차상장 + 비트겟 선물 가능 종목 {len(snapshot)}개 기준가 저장 완료\n\n09:00~09:15 동안 30초마다 최고가를 추적합니다."
    )

async def window_collect_job(bot, chat_id):
    state = load_state()
    if not state.get("running"):
        return

    snapshot = await get_crosslisted_futures_snapshot()
    window = update_window_with_snapshot(snapshot)
    print(f"[JOB] window updated: {len(window.get('symbols', {}))} symbols")

async def morning_scan_job(bot, chat_id):
    state = load_state()
    if not state.get("running"):
        return

    if state.get("open_position"):
        print("[JOB] 09:15 scan skipped: open position exists")
        return

    threshold = state["settings"]["pump_threshold_pct"]
    candidates, signal = get_peak_candidates(threshold, include_below=True, limit=20)

    await bot.send_message(chat_id=chat_id, text=scan_result_message(candidates, threshold, signal=signal, include_below=True))

    if not signal:
        return

    pos = create_position(signal, reason="09_00_TO_09_15_PEAK_PUMP_TOP1")
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

    # 09:00 기준가 저장
    scheduler.add_job(baseline_0900_job, "cron", hour=9, minute=0, args=[app.bot, chat_id])

    # 09:00~09:15 동안 30초마다 최고가 갱신
    scheduler.add_job(
        window_collect_job,
        "cron",
        hour=9,
        minute="0-14",
        second="0,30",
        args=[app.bot, chat_id]
    )

    # 09:15 최상위 펌핑 종목 1개 선정 및 PAPER 숏 진입
    scheduler.add_job(morning_scan_job, "cron", hour=9, minute=15, args=[app.bot, chat_id])

    # 오픈 포지션 감시
    scheduler.add_job(position_watch_job, "interval", seconds=30, args=[app.bot, chat_id])

    # 16시 손절 체크
    scheduler.add_job(sl_check_job, "cron", hour=16, minute=0, args=[app.bot, chat_id])

    scheduler.start()
    return scheduler
