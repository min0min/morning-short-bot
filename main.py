import asyncio
from datetime import datetime
import pytz

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, PAPER_SEED_USDT, KST_TIMEZONE, BOT_VERSION
from storage import load_state, save_state
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
    if not TELEGRAM_CHAT_ID:
        raise RuntimeError("TELEGRAM_CHAT_ID가 비어있습니다.")

    bootstrap_state()

    app = build_app()
    scheduler = setup_scheduler(app, TELEGRAM_CHAT_ID)

    print("====================================")
    print(f"Morning Short Paper Bot {BOT_VERSION} started.")
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
        await app.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=(
                f"🚀 [BOT STARTED]\n\nVersion : {BOT_VERSION}\n"
                f"Server Time : {now_kst_text()}\n"
                f"Timezone : {KST_TIMEZONE}\n"
                f"Scheduler : ON\n\n"
                f"등록된 Job:\n{jobs_text}"
            )
        )
    except Exception as e:
        print(f"[STARTUP MESSAGE ERROR] {type(e).__name__}: {e}")

    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
