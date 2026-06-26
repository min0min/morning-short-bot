import asyncio
from datetime import datetime
import pytz

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, PAPER_SEED_USDT, KST_TIMEZONE
from storage import load_state, save_state, get_active_chat_id
from telegram_bot import build_app
from scheduler import setup_scheduler

KST = pytz.timezone(KST_TIMEZONE)

def now_kst_text():
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")

def bootstrap_state():
    state = load_state()
    if not state.get("seed_usdt"):
        state["seed_usdt"] = PAPER_SEED_USDT
        state["paper_balance"] = PAPER_SEED_USDT
    save_state(state)

async def main():
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN이 비어있습니다.")

    bootstrap_state()

    app = build_app()
    scheduler = setup_scheduler(app, TELEGRAM_CHAT_ID)

    print("====================================")
    print("Morning Short Paper Bot FINAL v3.2 started.")
    print(f"Server Time KST: {now_kst_text()}")
    print(f"Timezone: {KST_TIMEZONE}")
    print(f"Scheduler running: {scheduler.running}")
    for job in scheduler.get_jobs():
        print(f"- {job.id} / next={job.next_run_time}")
    print("====================================")

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    try:
        jobs_text = "\n".join([f"- {job.id}\n  next: {job.next_run_time}" for job in scheduler.get_jobs()])
        startup_chat_id = get_active_chat_id()

        if startup_chat_id:
            await app.bot.send_message(
                chat_id=startup_chat_id,
                text=(
                    "🚀 [BOT STARTED]\n\n"
                    f"Server Time : {now_kst_text()}\n"
                    f"Timezone : {KST_TIMEZONE}\n"
                    f"Scheduler : ON\n\n"
                    f"등록된 Job:\n{jobs_text}\n\n"
                    "※ 알림 전송 기준: state.json active_chat_id"
                )
            )
        else:
            print("[STARTUP MESSAGE SKIP] active_chat_id is empty. Send /start to save chat_id.")
    except Exception as e:
        print(f"[STARTUP MESSAGE ERROR] {type(e).__name__}: {e}")
        print("Startup message failed, but scheduler is still running. Send /start to refresh active_chat_id.")

    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
