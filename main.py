import asyncio
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, PAPER_SEED_USDT
from storage import load_state, save_state
from telegram_bot import build_app
from scheduler import setup_scheduler

def bootstrap_state():
    state = load_state()
    if not state.get("seed_usdt"):
        state["seed_usdt"] = PAPER_SEED_USDT
        state["paper_balance"] = PAPER_SEED_USDT
    save_state(state)

async def main():
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN이 비어있습니다. .env를 확인하세요.")
    if not TELEGRAM_CHAT_ID:
        raise RuntimeError("TELEGRAM_CHAT_ID가 비어있습니다. .env를 확인하세요.")

    bootstrap_state()
    app = build_app()

    setup_scheduler(app, TELEGRAM_CHAT_ID)

    print("Morning Short Paper Bot started.")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
