from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

from config import TELEGRAM_BOT_TOKEN
from storage import load_state, save_state, load_trades
from messages import main_menu_text, status_message

WAITING_SEED = "waiting_seed"

def main_keyboard():
    rows = [
        [InlineKeyboardButton("🔑 API 키 등록", callback_data="api"), InlineKeyboardButton("💰 시드 설정", callback_data="seed")],
        [InlineKeyboardButton("▶️ 모의 시작", callback_data="start_paper"), InlineKeyboardButton("⏸ 모의 중지", callback_data="stop_paper")],
        [InlineKeyboardButton("📊 내 상태", callback_data="status"), InlineKeyboardButton("📋 거래 내역", callback_data="history")],
        [InlineKeyboardButton("💵 가상 수익 현황", callback_data="profit"), InlineKeyboardButton("📈 신호 통계", callback_data="stats")],
        [InlineKeyboardButton("⚙️ 비율·익절 설정", callback_data="settings")],
        [InlineKeyboardButton("🎯 종목 선정 기준", callback_data="criteria")],
        [InlineKeyboardButton("📢 안내사항", callback_data="notice")]
    ]
    return InlineKeyboardMarkup(rows)

async def send_main_menu(update_or_query):
    text = main_menu_text()
    if hasattr(update_or_query, "message") and update_or_query.message:
        await update_or_query.message.reply_text(text, reply_markup=main_keyboard())
    else:
        await update_or_query.edit_message_text(text, reply_markup=main_keyboard())

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_main_menu(update)

async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    state = load_state()

    if data == "seed":
        context.user_data[WAITING_SEED] = True
        await query.edit_message_text(
            "💰 시드 설정\n\n카피트레이딩에 사용할 총 시드(USDT)를 입력하세요.\n\n예) 1000 → 1,000 USDT 기준으로 비중 계산\n0 입력 시 → 향후 거래소 잔고 자동 조회\n\n❌ 취소하려면 /start",
        )
    elif data == "start_paper":
        state["running"] = True
        save_state(state)
        await query.edit_message_text("✅ 모의투자 시작\n\n상태 : PAPER MODE ON", reply_markup=main_keyboard())
    elif data == "stop_paper":
        state["running"] = False
        save_state(state)
        await query.edit_message_text("⏸ 모의투자 중지\n\n상태 : PAPER MODE OFF", reply_markup=main_keyboard())
    elif data == "status":
        await query.edit_message_text(status_message(state), reply_markup=main_keyboard())
    elif data == "history":
        trades = load_trades()[-5:]
        if not trades:
            msg = "📋 거래 내역\n\n아직 거래 내역이 없습니다."
        else:
            msg = "📋 최근 거래 내역\n\n"
            for t in trades:
                p = t.get("position", {})
                msg += f"- {t.get('type')} / {p.get('base')} / {p.get('close_reason', '')}\n"
        await query.edit_message_text(msg, reply_markup=main_keyboard())
    elif data == "profit":
        pnl = float(state["paper_balance"]) - float(state["seed_usdt"])
        await query.edit_message_text(f"💵 가상 수익 현황\n\n시작 시드 : ${state['seed_usdt']:,.2f}\n현재 잔고 : ${state['paper_balance']:,.2f}\n누적 손익 : ${pnl:,.2f}", reply_markup=main_keyboard())
    elif data == "settings":
        s = state["settings"]
        await query.edit_message_text(
            f"⚙️ 비율·익절 설정\n\n1차 : {s['entry_1_pct']*100:.1f}%\n2차 : {s['entry_2_pct']*100:.1f}%\n3차 : {s['entry_3_pct']*100:.1f}%\n레버리지 : {s['leverage']}배\n추가진입 간격 : +{s['add_entry_price_move_pct']}%\n익절 : +{s['tp_leveraged_pct']}%\n16시 손절 : {s['sl_leveraged_pct']}%",
            reply_markup=main_keyboard()
        )
    elif data == "criteria":
        await query.edit_message_text("🎯 종목 선정 기준\n\n09:15 KST\n업비트 + 빗썸 교차상장\n비트겟 USDT 선물 가능\n+3% 이상 급등\n상승률 1등 딱 1개만 거래", reply_markup=main_keyboard())
    elif data == "api":
        await query.edit_message_text("🔑 API 키 등록\n\n현재 v1.0은 PAPER MODE라 주문 API가 필요 없습니다.\n가격 조회는 공개 API로 진행합니다.", reply_markup=main_keyboard())
    elif data == "notice":
        await query.edit_message_text("📢 안내사항\n\n이 봇은 실주문을 넣지 않는 모의투자 봇입니다.\n실제 돈이 움직이지 않습니다.", reply_markup=main_keyboard())
    else:
        await query.edit_message_text("준비중입니다.", reply_markup=main_keyboard())

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get(WAITING_SEED):
        text = update.message.text.strip()
        try:
            value = float(text)
            if value == 0:
                await update.message.reply_text("🔄 0 입력 확인\n\n향후 거래소 잔고 자동 조회 모드로 연결 예정입니다.\n현재 PAPER v1.0에서는 고정 시드를 입력해주세요.")
                return
            if value <= 0:
                raise ValueError()

            state = load_state()
            state["seed_usdt"] = value
            state["paper_balance"] = value
            save_state(state)
            context.user_data[WAITING_SEED] = False
            await update.message.reply_text(
                f"✅ 가상 시드 설정 완료\n\n가상 증거금 : ${value:,.2f}\n\n1차 진입 : ${value*0.02:,.2f}\n2차 진입 : ${value*0.01:,.2f}\n3차 진입 : ${value*0.01:,.2f}",
                reply_markup=main_keyboard()
            )
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
