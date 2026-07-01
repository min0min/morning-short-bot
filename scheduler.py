from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import pytz
import traceback

from config import KST_TIMEZONE, REAL_FIXED_LEVERAGE, LIVE_STRATEGY_ENABLED, LIVE_DAILY_MAX_ENTRIES
from storage import (
    load_state,
    save_state,
    append_daily_signal,
    load_active_chat_id,
    load_bingx_api,
    set_current_user,
    list_users,
    iter_live_users,
    reset_live_daily_if_needed,
    save_live_entry,
    save_live_close,
    update_live_position_metrics,
    should_live_add_entry,
)
from scanner import scan_latest_closed_15m_oc
from bingx import (
    is_bingx_futures_listed,
    get_bingx_swap_balance,
    get_bingx_symbol_price,
    place_short_market_order_with_leverage,
    close_short_market_position_with_fills,
)
from messages import (
    scan_result_message,
    bingx_auto_listing_ok_message,
    bingx_auto_listing_skip_message,
    bingx_auto_listing_error_message,
    live_entry_success_message,
    live_add_success_message,
    live_close_success_message,
    live_entry_error_message,
    live_skip_message,
)

KST = pytz.timezone(KST_TIMEZONE)

def now_kst_text():
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")

def resolve_chat_id(default_chat_id=None):
    active = load_active_chat_id()
    if active:
        return active
    if default_chat_id:
        return str(default_chat_id)
    return None

async def safe_send(bot, chat_id, text):
    target_chat_id = str(chat_id) if chat_id else resolve_chat_id(chat_id)
    if not target_chat_id:
        print("[TELEGRAM SEND SKIP] no chat_id")
        return False
    try:
        await bot.send_message(chat_id=target_chat_id, text=text)
        return True
    except Exception as e:
        print(f"[TELEGRAM SEND ERROR] {type(e).__name__}: {e} target_chat_id={target_chat_id}")
        return False

def _entry_pct_by_level(level):
    return 0.02 if level == 1 else 0.01

async def _place_live_short_for_signal(signal, level=1):
    api = load_bingx_api()
    if not api:
        raise RuntimeError("BingX API가 등록되어 있지 않습니다.")

    balance = await get_bingx_swap_balance(api["api_key"], api["api_secret"])
    available = float(balance.get("available_usdt", 0) or 0)
    if available <= 0:
        raise RuntimeError(f"BingX 사용 가능 잔고가 0 이하입니다: {available}")

    entry_pct = _entry_pct_by_level(level)
    margin_usdt = available * entry_pct
    order_value_usdt = margin_usdt * REAL_FIXED_LEVERAGE

    symbol = signal.get("base") or signal.get("symbol")
    result = await place_short_market_order_with_leverage(
        api["api_key"],
        api["api_secret"],
        symbol,
        order_value_usdt,
        REAL_FIXED_LEVERAGE,
    )
    pos = save_live_entry(
        result,
        signal=signal,
        entry_level=level,
        margin_usdt=margin_usdt,
        order_value_usdt=order_value_usdt,
    )
    return pos, result, available, margin_usdt, order_value_usdt

async def scheduler_alive_job(bot, chat_id):
    users = list_users()
    live_users = [u for u in users if u.get("approval_status") == "APPROVED" and u.get("running")]
    print(f"[ALIVE] {now_kst_text()} users={len(users)} live={len(live_users)}")
    admin_or_active = resolve_chat_id(chat_id)
    await safe_send(
        bot,
        admin_or_active,
        "🟢 [SCHEDULER ALIVE]\n\n"
        f"시간 : {now_kst_text()}\n"
        f"등록 유저 : {len(users)}명\n"
        f"실행 유저 : {len(live_users)}명\n"
        f"실전 전략 : {'ON' if LIVE_STRATEGY_ENABLED else 'OFF'}\n\n"
        "09:15 멀티유저 실전 스캔 대기중"
    )

async def scan_ready_job(bot, chat_id):
    live_users = iter_live_users()
    await safe_send(
        bot,
        resolve_chat_id(chat_id),
        "🟡 [SCAN READY]\n\n"
        f"시간 : {now_kst_text()}\n"
        f"실행 유저 : {len(live_users)}명\n\n"
        "곧 09:15 마감 15분봉 O→C 스캔을 시작합니다.\n"
        "신호가 있으면 승인/실행 ON 유저별로 독립 주문합니다."
    )

async def _enter_for_user(bot, user_state, signal, attempt):
    uid = str(user_state.get("user_chat_id"))
    set_current_user(uid)
    state = reset_live_daily_if_needed(load_state())
    save_state(state)

    if state.get("approval_status") != "APPROVED":
        await safe_send(bot, uid, f"⛔ [LIVE ENTRY BLOCKED]\n\n승인 상태: {state.get('approval_status')}")
        return
    if not state.get("running"):
        return
    if state.get("live_position"):
        await safe_send(bot, uid, "⚠️ [LIVE ENTRY SKIP]\n\n이미 실전 오픈 포지션이 있어 신규 진입을 막았습니다.")
        return
    if int(state.get("live_daily_entry_count", 0) or 0) >= LIVE_DAILY_MAX_ENTRIES:
        await safe_send(bot, uid, "⚠️ [LIVE ENTRY SKIP]\n\n오늘 실전 진입 제한 1회를 이미 사용했습니다.")
        return

    try:
        pos, order_result, available, margin_usdt, order_value_usdt = await _place_live_short_for_signal(signal, level=1)
        print(f"[LIVE ENTRY USER] uid={uid} {pos.get('symbol')} avg={pos.get('avg_price')} qty={pos.get('qty')}")
        await safe_send(bot, uid, live_entry_success_message(pos, order_result, signal))
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        print(f"[LIVE ENTRY ERROR USER] uid={uid} {err}")
        print(traceback.format_exc())
        await safe_send(bot, uid, live_entry_error_message(err))

async def closed_15m_scan_job(bot, chat_id, attempt="PRIMARY"):
    print(f"[JOB START] multiuser closed_15m_scan_job {attempt} {now_kst_text()}")
    try:
        users = list_users()
        live_users = [u for u in users if u.get("approval_status") == "APPROVED" and u.get("running")]
        admin_or_active = resolve_chat_id(chat_id)

        if not LIVE_STRATEGY_ENABLED:
            await safe_send(bot, admin_or_active, live_skip_message("LIVE_STRATEGY_ENABLED=False"))
            return

        if not live_users:
            await safe_send(bot, admin_or_active, f"⏸ [09:15 LIVE SCAN SKIP / {attempt}]\n\n실행 ON 상태의 승인 유저가 없습니다.")
            return

        # strategy settings 기준은 첫 실행 유저 기준
        set_current_user(live_users[0].get("user_chat_id"))
        state = load_state()
        threshold = state["settings"]["pump_threshold_pct"]

        await safe_send(
            bot,
            admin_or_active,
            f"🟢 [09:15 MULTIUSER LIVE SCAN / {attempt}]\n\n"
            f"시간 : {now_kst_text()}\n"
            f"대상 유저 : {len(live_users)}명\n"
            "마감 15분봉 O→C 기준으로 실전 후보를 스캔합니다."
        )

        result = await scan_latest_closed_15m_oc(threshold)
        candidates = result.get("candidates", [])
        top20 = result.get("top20") or candidates[:20]
        passed = result.get("passed", [])
        signal = result.get("signal")

        print(
            f"[SCAN RESULT] attempt={attempt} target={result.get('target_open')} "
            f"total={result.get('total_symbols')} errors={result.get('errors')} "
            f"passed={len(passed)} signal={signal.get('base') if signal else None}"
        )

        # 모든 live user에게 daily signal 기록
        for u in live_users:
            set_current_user(u.get("user_chat_id"))
            append_daily_signal({
                "attempt": attempt,
                "target_open": result.get("target_open"),
                "total_symbols": result.get("total_symbols"),
                "errors": result.get("errors"),
                "passed_count": len(passed),
                "signal": signal,
                "top20": top20,
                "mode": "LIVE_MULTIUSER",
            })

        await safe_send(
            bot,
            admin_or_active,
            scan_result_message(
                top20,
                threshold,
                signal=signal,
                total_symbols=result["total_symbols"],
                errors=result["errors"],
                title=f"{result['target_open']} MULTIUSER LIVE SCAN / {attempt}"
            )
        )

        if not signal:
            if attempt == "FINAL_RETRY":
                await safe_send(bot, admin_or_active, "📭 [FINAL NO ENTRY]\n\n최종 재시도까지 진입 조건 충족 종목이 없습니다.")
            return

        try:
            listing = await is_bingx_futures_listed(signal.get("base") or signal.get("symbol"))
            if not listing.get("listed"):
                await safe_send(bot, admin_or_active, bingx_auto_listing_skip_message(signal, listing))
                return
            await safe_send(bot, admin_or_active, bingx_auto_listing_ok_message(signal, listing))
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            await safe_send(bot, admin_or_active, bingx_auto_listing_error_message(signal, err))
            return

        # 유저별 독립 실전 주문
        for u in live_users:
            await _enter_for_user(bot, u, signal, attempt)

    except Exception as e:
        print("[MULTIUSER SCAN ERROR]")
        print(traceback.format_exc())
        await safe_send(bot, resolve_chat_id(chat_id), f"❌ [09:15 MULTIUSER SCAN ERROR / {attempt}]\n\n{type(e).__name__}: {e}")

async def position_watch_job(bot, chat_id):
    try:
        for u in iter_live_users():
            uid = str(u.get("user_chat_id"))
            set_current_user(uid)
            state = load_state()
            pos = state.get("live_position")
            if not pos:
                continue

            api = load_bingx_api()
            if not api:
                continue

            price = await get_bingx_symbol_price(pos["symbol"])
            pos = update_live_position_metrics(price)
            pnl = float(pos.get("last_pnl_pct", 0) or 0)
            print(f"[LIVE WATCH USER] uid={uid} {pos.get('symbol')} price={price} pnl={pnl:.4f}%")

            add_level = should_live_add_entry(price)
            if add_level:
                signal = pos.get("signal") or {"base": pos.get("base"), "symbol": pos.get("symbol")}
                try:
                    new_pos, order_result, available, margin_usdt, order_value_usdt = await _place_live_short_for_signal(signal, level=add_level)
                    await safe_send(bot, uid, live_add_success_message(new_pos, order_result, add_level))
                except Exception as e:
                    await safe_send(bot, uid, f"❌ 실전 추가진입 실패\n\n{type(e).__name__}: {e}")

            state = load_state()
            pos = state.get("live_position")
            if pos and float(pos.get("last_pnl_pct", 0) or 0) >= float(state["settings"].get("tp_leveraged_pct", 12)):
                try:
                    close_result = await close_short_market_position_with_fills(api["api_key"], api["api_secret"], pos["symbol"])
                    try:
                        close_price = await get_bingx_symbol_price(pos["symbol"])
                    except Exception:
                        close_price = None
                    closed = save_live_close(close_result, close_price=close_price)
                    await safe_send(bot, uid, live_close_success_message(closed))
                except Exception as e:
                    await safe_send(bot, uid, f"❌ 실전 TP 청산 실패\n\n{type(e).__name__}: {e}\nBingX 앱에서 포지션을 직접 확인하세요.")
    except Exception as e:
        print(f"[MULTIUSER POSITION WATCH ERROR] {type(e).__name__}: {e}")

async def sl_check_job(bot, chat_id):
    print(f"[SL CHECK START] {now_kst_text()}")
    for u in iter_live_users():
        uid = str(u.get("user_chat_id"))
        try:
            set_current_user(uid)
            state = load_state()
            pos = state.get("live_position")
            if not pos:
                continue
            api = load_bingx_api()
            if not api:
                continue
            price = await get_bingx_symbol_price(pos["symbol"])
            pos = update_live_position_metrics(price)
            pnl = float(pos.get("last_pnl_pct", 0) or 0)
            sl = float(state["settings"].get("sl_leveraged_pct", -30))
            if pnl <= sl:
                close_result = await close_short_market_position_with_fills(api["api_key"], api["api_secret"], pos["symbol"])
                closed = save_live_close(close_result, close_price=price)
                await safe_send(bot, uid, live_close_success_message(closed))
            else:
                await safe_send(bot, uid, f"🕓 [16:00 LIVE SL CHECK]\n\n현재 손익률 {pnl:+.2f}%\n손절 기준 {sl:.2f}% 이하 아님 → 손절하지 않고 계속 홀딩합니다.\n이후에도 30초 감시는 유지되고, TP +12% 도달 시 자동 익절합니다.")
        except Exception as e:
            await safe_send(bot, uid, f"❌ [16:00 LIVE SL CHECK ERROR]\n\n{type(e).__name__}: {e}")

def setup_scheduler(app, chat_id):
    timezone = pytz.timezone(KST_TIMEZONE)
    scheduler = AsyncIOScheduler(timezone=timezone)

    scheduler.add_job(scheduler_alive_job, "cron", hour=8, minute=59, id="0859_scheduler_alive", args=[app.bot, chat_id], replace_existing=True)
    scheduler.add_job(scan_ready_job, "cron", hour=9, minute=14, id="0914_scan_ready", args=[app.bot, chat_id], replace_existing=True)

    scheduler.add_job(
        closed_15m_scan_job, "cron", hour=9, minute=15, second=20,
        id="0915_closed_15m_scan_primary", args=[app.bot, chat_id, "PRIMARY"],
        replace_existing=True, misfire_grace_time=300, coalesce=True, max_instances=1
    )
    scheduler.add_job(
        closed_15m_scan_job, "cron", hour=9, minute=16, second=10,
        id="0916_closed_15m_scan_retry", args=[app.bot, chat_id, "RETRY_1"],
        replace_existing=True, misfire_grace_time=300, coalesce=True, max_instances=1
    )
    scheduler.add_job(
        closed_15m_scan_job, "cron", hour=9, minute=17, second=10,
        id="0917_closed_15m_scan_final_retry", args=[app.bot, chat_id, "FINAL_RETRY"],
        replace_existing=True, misfire_grace_time=300, coalesce=True, max_instances=1
    )

    scheduler.add_job(
        position_watch_job, "interval", seconds=30, id="multiuser_live_position_watch_30s",
        args=[app.bot, chat_id], replace_existing=True, max_instances=1
    )
    scheduler.add_job(
        sl_check_job, "cron", hour=16, minute=0, id="1600_multiuser_live_sl_check",
        args=[app.bot, chat_id], replace_existing=True
    )

    scheduler.start()

    print("====================================")
    print("[MULTIUSER SCHEDULER REGISTERED]")
    print(f"Timezone: {KST_TIMEZONE}")
    for job in scheduler.get_jobs():
        print(f"- {job.id} next={job.next_run_time}")
    print("====================================")

    return scheduler
