from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import pytz
import traceback

from config import KST_TIMEZONE
from storage import load_state, append_daily_signal, load_active_chat_id
from exchanges import get_bitget_price
from scanner import scan_latest_closed_15m_oc
from bingx import is_bingx_futures_listed
from strategy import create_position, add_entry_if_needed, check_tp, check_sl_after_16, update_open_position_metrics
from messages import entry_message, add_message, close_message, scan_result_message, bingx_auto_listing_ok_message, bingx_auto_listing_skip_message, bingx_auto_listing_error_message

KST = pytz.timezone(KST_TIMEZONE)

def now_kst_text():
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")

def resolve_chat_id(default_chat_id=None):
    active = load_active_chat_id()
    if active:
        print(f"[CHAT SOURCE] active_chat.json chat_id={active}")
        return active
    if default_chat_id:
        print(f"[CHAT SOURCE] ENV TELEGRAM_CHAT_ID chat_id={default_chat_id}")
        return str(default_chat_id)
    print("[CHAT SOURCE] none")
    return None

async def safe_send(bot, chat_id, text):
    target_chat_id = resolve_chat_id(chat_id)
    if not target_chat_id:
        print("[TELEGRAM SEND SKIP] no chat_id. Send /start first.")
        return False

    try:
        await bot.send_message(chat_id=target_chat_id, text=text)
        return True
    except Exception as e:
        print(f"[TELEGRAM SEND ERROR] {type(e).__name__}: {e} target_chat_id={target_chat_id}")
        return False

async def scheduler_alive_job(bot, chat_id):
    state = load_state()
    print(f"[ALIVE] {now_kst_text()} running={state.get('running')}")
    await safe_send(
        bot,
        chat_id,
        "🟢 [SCHEDULER ALIVE]\n\n"
        f"시간 : {now_kst_text()}\n"
        f"모의 실행 : {'ON' if state.get('running') else 'OFF'}\n\n"
        "09:15 마감 15분봉 스캔 대기중"
    )

async def scan_ready_job(bot, chat_id):
    state = load_state()
    print(f"[SCAN READY] {now_kst_text()} running={state.get('running')}")
    await safe_send(
        bot,
        chat_id,
        "🟡 [SCAN READY]\n\n"
        f"시간 : {now_kst_text()}\n"
        f"모의 실행 : {'ON' if state.get('running') else 'OFF'}\n\n"
        "09:15 마감봉 확정 후 20초 뒤 스캔합니다.\n"
        "캔들 반영 지연 가능성 때문에 09:16, 09:17에 자동 재시도합니다."
    )

async def closed_15m_scan_job(bot, chat_id, attempt="PRIMARY"):
    print(f"[JOB START] closed_15m_scan_job {attempt} {now_kst_text()}")

    try:
        state = load_state()
        print(f"[STATE] attempt={attempt} running={state.get('running')} open_position={bool(state.get('open_position'))}")

        await safe_send(
            bot,
            chat_id,
            f"🟢 [09:15 SCAN START / {attempt}]\n\n"
            f"시간 : {now_kst_text()}\n"
            "실시간/백테스트 통합 함수로 마감 15분봉 O→C 스캔을 시작합니다."
        )

        if not state.get("running"):
            print("[SCAN SKIP] paper mode off")
            await safe_send(bot, chat_id, f"⏸ [09:15 SCAN SKIP / {attempt}]\n\n모의 실행 OFF 상태라 스캔을 건너뜁니다.")
            return

        if state.get("open_position"):
            print("[SCAN SKIP] open position exists")
            await safe_send(bot, chat_id, f"⚠️ [09:15 SCAN SKIP / {attempt}]\n\n이미 오픈 포지션이 있어서 신규 진입을 막았습니다.")
            return

        threshold = state["settings"]["pump_threshold_pct"]
        result = await scan_latest_closed_15m_oc(threshold)

        candidates = result.get("candidates", [])
        top20 = result.get("top20") or candidates[:20]
        passed = result.get("passed", [])
        signal = result.get("signal")

        print(
            f"[SCAN RESULT] attempt={attempt} target={result.get('target_open')} "
            f"total={result.get('total_symbols')} errors={result.get('errors')} "
            f"candidates={len(candidates)} passed={len(passed)} "
            f"signal={signal.get('base') if signal else None}"
        )

        if top20:
            best = top20[0]
            print(f"[SCAN TOP1] {best['base']} oc={best['change_pct']:.4f} passed={best.get('passed')}")
        if signal:
            print(f"[SCAN SIGNAL] {signal['base']} oc={signal['change_pct']:.4f}")

        append_daily_signal({
            "attempt": attempt,
            "target_open": result.get("target_open"),
            "total_symbols": result.get("total_symbols"),
            "errors": result.get("errors"),
            "passed_count": len(passed),
            "signal": signal,
            "top20": top20,
        })

        await safe_send(
            bot,
            chat_id,
            scan_result_message(
                top20,
                threshold,
                signal=signal,
                total_symbols=result["total_symbols"],
                errors=result["errors"],
                title=f"{result['target_open']} 마감 15분봉 SCAN / {attempt}"
            )
        )

        if not signal:
            print(f"[SCAN END] no signal attempt={attempt}")
            if attempt != "FINAL_RETRY":
                await safe_send(
                    bot,
                    chat_id,
                    f"🟠 [NO ENTRY / {attempt}]\n\n"
                    f"통과 후보: {len(passed)}개\n"
                    "다음 재시도에서 다시 확인합니다."
                )
            else:
                await safe_send(
                    bot,
                    chat_id,
                    "📭 [FINAL NO ENTRY]\n\n"
                    "최종 재시도까지 완료했지만 진입 조건 충족 종목이 없습니다."
                )
            return

        latest_state = load_state()
        if latest_state.get("open_position"):
            print("[ENTRY SKIP] open position appeared before entry")
            await safe_send(bot, chat_id, "⚠️ [ENTRY SKIP]\n\n이미 오픈 포지션이 생겨 중복 진입을 막았습니다.")
            return

        # v4.2: BingX 자동 상장 여부 확인
        try:
            listing = await is_bingx_futures_listed(signal.get("base") or signal.get("symbol"))
            print(
                f"[BINGX LISTING] base={signal.get('base')} "
                f"listed={listing.get('listed')} symbol={listing.get('symbol')} raw={listing.get('raw_symbol')}"
            )

            if not listing.get("listed"):
                await safe_send(bot, chat_id, bingx_auto_listing_skip_message(signal, listing))
                print(f"[ENTRY SKIP] BingX not listed base={signal.get('base')}")
                return

            await safe_send(bot, chat_id, bingx_auto_listing_ok_message(signal, listing))

        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            print(f"[BINGX LISTING ERROR] {err}")
            await safe_send(bot, chat_id, bingx_auto_listing_error_message(signal, err))
            return

        pos = create_position(signal, reason=f"CLOSED_15M_OC_TOP1_{attempt}")
        print(f"[ENTRY] attempt={attempt} {pos['base']} {pos['symbol']} price={pos['entries'][0]['price']}")
        await safe_send(bot, chat_id, entry_message(pos, signal))

    except Exception as e:
        print("[SCAN ERROR]")
        print(traceback.format_exc())
        await safe_send(
            bot,
            chat_id,
            f"❌ [09:15 SCAN ERROR / {attempt}]\n\n{type(e).__name__}: {e}\n\nRailway 로그를 확인하세요."
        )

async def position_watch_job(bot, chat_id):
    try:
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
            print(f"[ADD ENTRY] {new_pos['base']} level={entry['level']} price={entry['price']}")
            await safe_send(bot, chat_id, add_message(entry, new_pos))

        closed = check_tp(price)
        if closed:
            closed_pos, balance = closed
            print(f"[TP CLOSE] {closed_pos['base']} pnl={closed_pos.get('pnl_pct')}")
            await safe_send(bot, chat_id, close_message(closed_pos, balance))

    except Exception as e:
        print(f"[POSITION WATCH ERROR] {type(e).__name__}: {e}")

async def sl_check_job(bot, chat_id):
    print(f"[SL CHECK START] {now_kst_text()}")

    try:
        state = load_state()
        if not state.get("running"):
            print("[SL SKIP] paper mode off")
            return

        pos = state.get("open_position")
        if not pos:
            print("[SL SKIP] no open position")
            return

        price = await get_bitget_price(pos["symbol"])
        update_open_position_metrics(price)

        closed = check_sl_after_16(price)
        if closed:
            closed_pos, balance = closed
            print(f"[SL CLOSE] {closed_pos['base']} pnl={closed_pos.get('pnl_pct')}")
            await safe_send(bot, chat_id, close_message(closed_pos, balance))
        else:
            await safe_send(bot, chat_id, "🕓 [16:00 SL CHECK]\n\n-30% 이하 손실 아님 → 홀딩 유지")

    except Exception as e:
        print(f"[SL CHECK ERROR] {type(e).__name__}: {e}")
        await safe_send(bot, chat_id, f"❌ [16:00 SL CHECK ERROR]\n\n{type(e).__name__}: {e}")

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
        position_watch_job, "interval", seconds=30, id="position_watch_30s",
        args=[app.bot, chat_id], replace_existing=True, max_instances=1
    )
    scheduler.add_job(
        sl_check_job, "cron", hour=16, minute=0, id="1600_sl_check",
        args=[app.bot, chat_id], replace_existing=True
    )

    scheduler.start()

    print("====================================")
    print("[SCHEDULER REGISTERED]")
    print(f"Timezone: {KST_TIMEZONE}")
    for job in scheduler.get_jobs():
        print(f"- {job.id} next={job.next_run_time}")
    print("====================================")

    return scheduler
