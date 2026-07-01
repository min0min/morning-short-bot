from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

from config import TELEGRAM_BOT_TOKEN, BOT_VERSION, REAL_TEST_SYMBOL, REAL_TEST_MARGIN_USDT, ADMIN_CHAT_ID
from storage import load_state, save_state, load_trades, calc_trade_stats, save_active_chat_id, save_bingx_api, mark_bingx_api_tested, set_seed_auto_mode, set_seed_fixed_mode, load_bingx_api, save_real_test_open, save_real_test_close, get_real_test_stats, get_live_trade_stats, get_admin_user_snapshot, set_user_pending_approval, approve_user, reject_user, pause_user
from messages import (
    main_menu_text,
    status_message,
    entry_message,
    scan_result_message,
    backtest_result_message,
    weekly_backtest_result_message,
    stats_message,
    api_register_guide_message,
    seed_setting_message,
    bingx_connection_success_message,
    bingx_connection_fail_message,
    real_order_test_warning_message,
    real_order_success_message,
    real_order_fail_message,
    real_close_success_message,
    real_close_fail_message,
    real_close_success_message_with_pnl,
    real_test_stats_message,
    live_profit_message,
    admin_approval_request_message,
    user_approval_waiting_message,
    user_approved_message,
    user_rejected_message,
    start_blocked_by_approval_message,
    admin_monitor_message,
)
from exchanges import get_crosslisted_futures_snapshot, get_exchange_debug_text
from strategy import create_position
from backtest import run_date_backtest, run_recent_days_backtest
from scanner import scan_latest_closed_15m_oc
from bingx import test_bingx_read_connection, get_bingx_swap_balance, place_short_market_order, close_short_market_position, get_bingx_symbol_price

WAITING_SEED = "waiting_seed"
WAITING_BACKTEST_DATE = "waiting_backtest_date"
WAITING_BINGX_API_KEY = "waiting_bingx_api_key"
WAITING_BINGX_API_SECRET = "waiting_bingx_api_secret"
TEMP_BINGX_API_KEY = "temp_bingx_api_key"

def main_keyboard(chat_id=None):
    rows = [
        [InlineKeyboardButton("🔑 API 키 등록", callback_data="api"), InlineKeyboardButton("💰 시드 설정", callback_data="seed")],
        [InlineKeyboardButton("▶️ 트레이딩 시작", callback_data="start_paper"), InlineKeyboardButton("⏸ 트레이딩 중지", callback_data="stop_paper")],
        [InlineKeyboardButton("📊 내 상태", callback_data="status"), InlineKeyboardButton("📋 거래 내역", callback_data="history")],
        [InlineKeyboardButton("💵 수익 현황", callback_data="profit"), InlineKeyboardButton("📈 신호 통계", callback_data="stats")],
        [InlineKeyboardButton("⚙️ 비율·익절 설정", callback_data="settings")],
        [InlineKeyboardButton("🎯 종목 선정 기준", callback_data="criteria")],
        [InlineKeyboardButton("🧪 마감 15분봉 즉시 테스트", callback_data="closed_15m_test")],
        [InlineKeyboardButton("🧪 날짜 백테스트", callback_data="date_backtest")],
        [InlineKeyboardButton("🧪 최근 7일 자동 검증", callback_data="recent7_backtest")],
        [InlineKeyboardButton("🔍 거래소 디버그", callback_data="debug_exchange")],
        [InlineKeyboardButton("🧪 실전 주문 테스트", callback_data="real_order_test"), InlineKeyboardButton("🧪 실전 테스트 청산", callback_data="real_close_test")],
        [InlineKeyboardButton("📢 안내사항", callback_data="notice")],
    ]
    if chat_id is not None and str(chat_id) == str(ADMIN_CHAT_ID):
        rows.append([InlineKeyboardButton("👑 관리자", callback_data="admin_monitor")])
    return InlineKeyboardMarkup(rows)


def api_agree_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ 동의하고 등록", callback_data="api_agree")],
        [InlineKeyboardButton("❌ 취소", callback_data="cancel_to_menu")],
    ])


def real_order_confirm_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ 1USDT SHORT 테스트 실행", callback_data="real_order_confirm")],
        [InlineKeyboardButton("❌ 취소", callback_data="cancel_to_menu")],
    ])




def admin_monitor_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 새로고침", callback_data="admin_monitor"),
            InlineKeyboardButton("⏸ 강제 중지", callback_data="admin_force_stop"),
        ],
        [InlineKeyboardButton("↩️ 메인 메뉴", callback_data="back_to_main_edit")],
    ])

def admin_approval_keyboard(chat_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ 승인", callback_data=f"admin_approve:{chat_id}"),
            InlineKeyboardButton("❌ 거절", callback_data=f"admin_reject:{chat_id}"),
        ],
        [InlineKeyboardButton("⏸ 보류/일시정지", callback_data=f"admin_pause:{chat_id}")],
    ])

def is_admin_chat(chat_id):
    return str(chat_id) == str(ADMIN_CHAT_ID)


async def send_admin_approval_request(context, chat_id, balance=None):
    state = set_user_pending_approval(chat_id)
    admin_id = str(ADMIN_CHAT_ID or "")
    if not admin_id:
        print("[ADMIN APPROVAL SKIP] ADMIN_CHAT_ID empty")
        return
    try:
        await context.bot.send_message(
            chat_id=admin_id,
            text=admin_approval_request_message(state, balance),
            reply_markup=admin_approval_keyboard(chat_id)
        )
    except Exception as e:
        print(f"[ADMIN APPROVAL SEND ERROR] {type(e).__name__}: {e}")



def detail_back_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("↩️ 메인 메뉴", callback_data="back_to_main_edit")]
    ])

def back_to_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("↩️ 메인 메뉴", callback_data="cancel_to_menu")]
    ])

async def send_main_menu(update_or_query):
    chat_id = None
    try:
        chat_id = update_or_query.effective_chat.id
    except Exception:
        try:
            chat_id = update_or_query.message.chat_id
        except Exception:
            chat_id = None

    if hasattr(update_or_query, "message") and update_or_query.message:
        await update_or_query.message.reply_text(main_menu_text(), reply_markup=main_keyboard(chat_id))
    else:
        await update_or_query.edit_message_text(main_menu_text(), reply_markup=main_keyboard(chat_id))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    save_active_chat_id(chat_id)
    await update.message.reply_text(
        f"✅ CHAT ID 저장 완료\n현재 chat_id: {chat_id}\n버전: {BOT_VERSION}"
    )
    await send_main_menu(update)

async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if update.effective_chat:
        save_active_chat_id(update.effective_chat.id)
    state = load_state()

    if data.startswith("admin_approve:"):
        target_chat_id = data.split(":", 1)[1]
        if not is_admin_chat(update.effective_chat.id):
            await query.edit_message_text("⛔ 관리자만 승인할 수 있습니다.")
            return
        approve_user(target_chat_id)
        await query.edit_message_text(f"✅ 승인 완료\n\nchat_id: {target_chat_id}")
        try:
            await context.bot.send_message(chat_id=target_chat_id, text=user_approved_message(), reply_markup=main_keyboard())
        except Exception as e:
            print(f"[APPROVAL USER NOTIFY ERROR] {type(e).__name__}: {e}")
        return

    elif data.startswith("admin_reject:"):
        target_chat_id = data.split(":", 1)[1]
        if not is_admin_chat(update.effective_chat.id):
            await query.edit_message_text("⛔ 관리자만 거절할 수 있습니다.")
            return
        reject_user(target_chat_id)
        await query.edit_message_text(f"❌ 승인 거절\n\nchat_id: {target_chat_id}")
        try:
            await context.bot.send_message(chat_id=target_chat_id, text=user_rejected_message(), reply_markup=main_keyboard())
        except Exception as e:
            print(f"[REJECT USER NOTIFY ERROR] {type(e).__name__}: {e}")
        return

    elif data.startswith("admin_pause:"):
        target_chat_id = data.split(":", 1)[1]
        if not is_admin_chat(update.effective_chat.id):
            await query.edit_message_text("⛔ 관리자만 보류할 수 있습니다.")
            return
        pause_user(target_chat_id)
        await query.edit_message_text(f"⏸ 보류/일시정지 완료\n\nchat_id: {target_chat_id}")
        try:
            await context.bot.send_message(chat_id=target_chat_id, text="⏸ 관리자에 의해 보류/일시정지 상태가 되었습니다.", reply_markup=main_keyboard())
        except Exception as e:
            print(f"[PAUSE USER NOTIFY ERROR] {type(e).__name__}: {e}")
        return

    if data == "back_to_main_edit":
        await query.edit_message_text(main_menu_text(), reply_markup=main_keyboard(update.effective_chat.id))
        return

    elif data == "admin_monitor":
        if not is_admin_chat(update.effective_chat.id):
            await query.edit_message_text("⛔ 관리자만 접근할 수 있습니다.", reply_markup=main_keyboard(update.effective_chat.id))
            return

        balance = None
        try:
            api = load_bingx_api()
            if api:
                bal = await get_bingx_swap_balance(api["api_key"], api["api_secret"])
                balance = bal.get("available_usdt")
        except Exception as e:
            print(f"[ADMIN MONITOR BALANCE ERROR] {type(e).__name__}: {e}")

        snapshot = get_admin_user_snapshot()
        await query.edit_message_text(admin_monitor_message(snapshot, balance), reply_markup=admin_monitor_keyboard())
        return

    elif data == "admin_force_stop":
        if not is_admin_chat(update.effective_chat.id):
            await query.edit_message_text("⛔ 관리자만 사용할 수 있습니다.", reply_markup=main_keyboard(update.effective_chat.id))
            return
        state = load_state()
        state["running"] = False
        save_state(state)
        await query.edit_message_text("⏸ 관리자 강제 중지 완료\n\n트레이딩 실행: OFF", reply_markup=admin_monitor_keyboard())
        return

    if data == "seed":
        context.user_data[WAITING_SEED] = True
        await query.edit_message_text(seed_setting_message())

    elif data == "start_paper":
        state = load_state()
        if state.get("approval_status") != "APPROVED":
            await query.edit_message_text(
                start_blocked_by_approval_message(state.get("approval_status")),
                reply_markup=main_keyboard()
            )
            return
        state["running"] = True
        save_state(state)
        await query.edit_message_text("✅ 트레이딩 시작\n\n상태 : LIVE TRADING ON", reply_markup=main_keyboard())

    elif data == "stop_paper":
        state["running"] = False
        save_state(state)
        await query.edit_message_text("⏸ 트레이딩 중지\n\n상태 : TRADING MODE OFF", reply_markup=main_keyboard())

    elif data == "status":
        live_balance = None
        try:
            api = load_bingx_api()
            if api:
                bal = await get_bingx_swap_balance(api["api_key"], api["api_secret"])
                live_balance = bal.get("available_usdt")
        except Exception as e:
            print(f"[STATUS BALANCE ERROR] {type(e).__name__}: {e}")
        await query.edit_message_text(status_message(load_state(), live_balance), reply_markup=main_keyboard())

    elif data == "history":
        trades = load_trades()[-7:]
        if not trades:
            msg = "📋 거래 내역\n\n아직 거래 내역이 없습니다."
        else:
            msg = "📋 최근 거래 내역\n\n"
            for t in trades:
                p = t.get("position", {})
                pnl = p.get("realized_pnl")
                pnl_txt = ""
                if pnl is not None:
                    pnl_txt = f" / PnL ${float(pnl):,.4f}"
                msg += f"- {t.get('type')} / {p.get('base') or p.get('symbol')} / {t.get('reason', p.get('close_reason', ''))}{pnl_txt}\n"
        await query.edit_message_text(msg, reply_markup=main_keyboard())

    elif data == "profit":
        try:
            stats = get_live_trade_stats, get_admin_user_snapshot()
            if isinstance(stats, tuple):
                stats = stats[-1] if stats and isinstance(stats[-1], dict) else {}
            msg = live_profit_message(stats)
        except Exception as e:
            msg = f"❌ 수익현황 조회 오류\n\n{type(e).__name__}: {e}"

        await query.message.reply_text(msg, reply_markup=detail_back_keyboard())
        return

    elif data == "stats":
        stats = calc_trade_stats()
        await query.edit_message_text(stats_message(stats), reply_markup=main_keyboard())

    elif data == "settings":
        s = state["settings"]
        await query.edit_message_text(
            f"⚙️ 비율·익절 설정\n\n1차 : {s['entry_1_pct']*100:.1f}%\n2차 : {s['entry_2_pct']*100:.1f}%\n3차 : {s['entry_3_pct']*100:.1f}%\n레버리지 : 4배 고정\n추가진입 간격 : +{s['add_entry_price_move_pct']}%\n익절 : +{s['tp_leveraged_pct']}%\n16시 손절 : {s['sl_leveraged_pct']}%",
            reply_markup=main_keyboard()
        )

    elif data == "criteria":
        await query.edit_message_text(
            "🎯 종목 선정 기준\n\n비트겟 선물 15분봉 기준\n09:00에 시작한 15분봉이 09:15에 마감\n마감봉 O→C 상승률 +3% 이상\n업비트 + 빗썸 교차상장 확인\n그중 상승률 1등 딱 1개만 PAPER 숏 진입\n\nTP: 레버리지 기준 +12%\nSL: 16:00 이후 레버리지 기준 -30%",
            reply_markup=main_keyboard()
        )

    elif data == "closed_15m_test":
        try:
            threshold = state["settings"]["pump_threshold_pct"]
            result = await scan_latest_closed_15m_oc(threshold)
            msg = scan_result_message(
                result["candidates"],
                threshold,
                signal=result["signal"],
                total_symbols=result["total_symbols"],
                errors=result["errors"],
                title=f"{result['target_open']} 마감 15분봉 즉시 테스트"
            )

            if result["signal"] and not state.get("open_position"):
                pos = create_position(result["signal"], reason="MANUAL_CLOSED_15M_TEST")
                msg += "\n\n" + entry_message(pos, result["signal"])
            elif result["signal"] and state.get("open_position"):
                msg += "\n\n⚠️ 이미 오픈 포지션이 있어서 중복 진입은 막았습니다."

            await query.edit_message_text(msg, reply_markup=main_keyboard())

        except Exception as e:
            await query.edit_message_text(f"❌ 마감 15분봉 즉시 테스트 실패\n\n{type(e).__name__}: {e}", reply_markup=main_keyboard())

    elif data == "date_backtest":
        context.user_data[WAITING_BACKTEST_DATE] = True
        await query.edit_message_text(
            "🧪 날짜 백테스트\n\n조회할 날짜를 입력하세요.\n\n예) 2026-06-25\n\n해당 날짜의 KST 09:00~09:15 마감 15분봉 O→C 기준으로 재현합니다.",
            reply_markup=main_keyboard()
        )

    elif data == "recent7_backtest":
        try:
            threshold = state["settings"]["pump_threshold_pct"]
            await query.edit_message_text(
                "🧪 최근 7일 자동 검증 실행중...\n\nKST 09:00~09:15 마감 15분봉 O→C 기준으로 계산합니다.\n종목 수가 많아서 1~3분 정도 걸릴 수 있습니다.",
                reply_markup=main_keyboard()
            )

            results = await run_recent_days_backtest(7, threshold)
            msg = weekly_backtest_result_message(results, threshold)
            await query.message.reply_text(msg, reply_markup=detail_back_keyboard())

        except Exception as e:
            await query.message.reply_text(
                f"❌ 최근 7일 자동 검증 실패\n\n{type(e).__name__}: {e}",
                reply_markup=main_keyboard()
            )

    elif data == "debug_exchange":
        try:
            snapshot = await get_crosslisted_futures_snapshot()
            await query.edit_message_text(
                f"🔍 [거래소 디버그 실행 완료]\n\n스냅샷 종목 수: {len(snapshot)}개\n\n{get_exchange_debug_text()}",
                reply_markup=main_keyboard()
            )
        except Exception as e:
            await query.edit_message_text(
                f"❌ 거래소 디버그 실패\n\n{type(e).__name__}: {e}\n\n{get_exchange_debug_text()}",
                reply_markup=main_keyboard()
            )

    elif data == "real_order_test":
        await query.edit_message_text(
            real_order_test_warning_message(REAL_TEST_SYMBOL, REAL_TEST_MARGIN_USDT),
            reply_markup=real_order_confirm_keyboard()
        )

    elif data == "real_order_confirm":
        api = load_bingx_api()
        if not api:
            await query.edit_message_text(
                "❌ BingX API가 등록되어 있지 않습니다.\n먼저 🔑 API 키 등록을 진행해주세요.",
                reply_markup=main_keyboard()
            )
            return

        await query.edit_message_text(
            f"🧪 실전 테스트 주문 전송중...\n심볼: {REAL_TEST_SYMBOL}\n금액: ${REAL_TEST_MARGIN_USDT}"
        )
        try:
            result = await place_short_market_order(
                api["api_key"],
                api["api_secret"],
                REAL_TEST_SYMBOL,
                REAL_TEST_MARGIN_USDT,
            )
            save_real_test_open(result)
            await query.message.reply_text(real_order_success_message(result), reply_markup=main_keyboard())
        except Exception as e:
            await query.message.reply_text(
                real_order_fail_message(f"{type(e).__name__}: {e}"),
                reply_markup=main_keyboard()
            )

    elif data == "real_close_test":
        api = load_bingx_api()
        if not api:
            await query.edit_message_text(
                "❌ BingX API가 등록되어 있지 않습니다.\n먼저 🔑 API 키 등록을 진행해주세요.",
                reply_markup=main_keyboard()
            )
            return

        await query.edit_message_text(f"🧪 실전 테스트 포지션 청산 시도중...\n심볼: {REAL_TEST_SYMBOL}")
        try:
            result = await close_short_market_position(
                api["api_key"],
                api["api_secret"],
                REAL_TEST_SYMBOL,
            )
            try:
                close_price = await get_bingx_symbol_price(REAL_TEST_SYMBOL)
            except Exception:
                close_price = None
            closed_pos = save_real_test_close(result, close_price=close_price)
            await query.message.reply_text(real_close_success_message_with_pnl(result, closed_pos), reply_markup=main_keyboard())
        except Exception as e:
            await query.message.reply_text(
                real_close_fail_message(f"{type(e).__name__}: {e}"),
                reply_markup=main_keyboard()
            )

    elif data == "api":
        await query.edit_message_text(api_register_guide_message(), reply_markup=api_agree_keyboard())

    elif data == "api_agree":
        context.user_data[WAITING_BINGX_API_KEY] = True
        await query.edit_message_text(
            "🔑 BingX API Key를 입력해주세요.\n\n입력한 메시지는 등록 후 즉시 삭제를 시도합니다.\n❌ 취소하려면 /start"
        )

    elif data == "cancel_to_menu":
        await query.edit_message_text(main_menu_text(), reply_markup=main_keyboard(update.effective_chat.id))

    elif data == "notice":
        await query.edit_message_text(
            "📢 안내사항\n\n버전: {BOT_VERSION}\n\n이 봇은 실주문을 넣지 않는 모의투자 봇입니다.\n실제 돈이 움직이지 않습니다.\n\n기준: 비트겟 선물 마감 15분봉 O→C +3% 이상, 업비트+빗썸 교차상장, 1등만 PAPER 숏 진입.",
            reply_markup=main_keyboard()
        )

    else:
        await query.edit_message_text("준비중입니다.", reply_markup=main_keyboard())

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat:
        save_active_chat_id(update.effective_chat.id)
    if context.user_data.get(WAITING_BINGX_API_KEY):
        api_key = update.message.text.strip()
        context.user_data[WAITING_BINGX_API_KEY] = False
        context.user_data[TEMP_BINGX_API_KEY] = api_key
        context.user_data[WAITING_BINGX_API_SECRET] = True

        try:
            await update.message.delete()
        except Exception:
            pass

        await update.message.reply_text(
            "✅ API Key 입력 완료!\n\n이제 Secret Key를 입력해주세요.\n입력한 메시지는 등록 후 즉시 삭제를 시도합니다.\n❌ 취소하려면 /start"
        )
        return

    if context.user_data.get(WAITING_BINGX_API_SECRET):
        api_secret = update.message.text.strip()
        api_key = context.user_data.get(TEMP_BINGX_API_KEY)

        context.user_data[WAITING_BINGX_API_SECRET] = False
        context.user_data[TEMP_BINGX_API_KEY] = None

        try:
            await update.message.delete()
        except Exception:
            pass

        if not api_key or not api_secret:
            await update.message.reply_text("❌ API 정보가 비어있습니다. /start 후 다시 등록해주세요.", reply_markup=main_keyboard())
            return

        save_bingx_api(api_key, api_secret)

        checking_msg = await update.message.reply_text("🔍 BingX API 연결 테스트중...\n잔고 조회가 가능한지 확인합니다.")

        try:
            result = await test_bingx_read_connection(api_key, api_secret)
            mark_bingx_api_tested(True)
            await checking_msg.edit_text(
                bingx_connection_success_message(result["available_usdt"], result["positions_count"]),
                reply_markup=main_keyboard()
            )
        except Exception as e:
            mark_bingx_api_tested(False)
            await checking_msg.edit_text(
                bingx_connection_fail_message(f"{type(e).__name__}: {e}"),
                reply_markup=main_keyboard()
            )
        return

    if context.user_data.get(WAITING_BACKTEST_DATE):
        date_text = update.message.text.strip()
        try:
            from datetime import datetime
            datetime.strptime(date_text, "%Y-%m-%d")

            context.user_data[WAITING_BACKTEST_DATE] = False
            await update.message.reply_text(
                f"🧪 날짜 백테스트 실행중...\n\n날짜 : {date_text}\n구간 : 09:00~09:15 KST 마감 15분봉 O→C\n\n종목 수가 많아서 10~60초 정도 걸릴 수 있습니다."
            )

            state = load_state()
            threshold = state["settings"]["pump_threshold_pct"]
            result = await run_date_backtest(date_text, threshold)
            msg = backtest_result_message(
                date_text,
                result["candidates"],
                threshold,
                result["total_symbols"],
                result["errors"],
            )
            await update.message.reply_text(msg, reply_markup=main_keyboard())
            return

        except Exception as e:
            context.user_data[WAITING_BACKTEST_DATE] = False
            await update.message.reply_text(
                f"❌ 날짜 백테스트 실패\n\n{type(e).__name__}: {e}",
                reply_markup=main_keyboard()
            )
            return

    if context.user_data.get(WAITING_SEED):
        text = update.message.text.strip()
        try:
            value = float(text)
            if value == 0:
                api = load_bingx_api()
                if not api:
                    await update.message.reply_text("❌ BingX API가 등록되어 있지 않습니다.\n먼저 🔑 API 키 등록을 진행해주세요.", reply_markup=main_keyboard())
                    return

                result = await get_bingx_swap_balance(api["api_key"], api["api_secret"])
                available = float(result["available_usdt"])

                set_seed_auto_mode()
                context.user_data[WAITING_SEED] = False

                await update.message.reply_text(
                    f"✅ 시드 자동조회 모드 설정 완료\n\nBingX 사용 가능 잔고 : ${available:,.2f}\n\n다음 진입부터 매번 거래소 잔고를 다시 조회해서 비중을 계산합니다.\n\n1차 2% : ${available*0.02:,.2f}\n2차 1% : ${available*0.01:,.2f}\n3차 1% : ${available*0.01:,.2f}\n\n상태 : 승인 대기",
                    reply_markup=main_keyboard()
                )
                await update.message.reply_text(user_approval_waiting_message(), reply_markup=main_keyboard())
                await send_admin_approval_request(context, update.effective_chat.id, available)
                return

            if value <= 0:
                raise ValueError()

            set_seed_fixed_mode(value)
            context.user_data[WAITING_SEED] = False
            await update.message.reply_text(
                f"✅ 고정 시드 설정 완료\n\n기준 시드 : ${value:,.2f}\n\n1차 진입 : ${value*0.02:,.2f}\n2차 진입 : ${value*0.01:,.2f}\n3차 진입 : ${value*0.01:,.2f}\n\n상태 : 승인 대기",
                reply_markup=main_keyboard()
            )
            await update.message.reply_text(user_approval_waiting_message(), reply_markup=main_keyboard())
            await send_admin_approval_request(context, update.effective_chat.id, value)
        except Exception:
            await update.message.reply_text("숫자로 입력해주세요. 예) 1000")
    else:
        await update.message.reply_text("메뉴를 열려면 /start 를 입력하세요.")

def build_app():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    return app
