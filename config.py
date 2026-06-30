import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

MODE = os.getenv("MODE", "PAPER")
PAPER_SEED_USDT = float(os.getenv("PAPER_SEED_USDT", "1000"))

KST_TIMEZONE = "Asia/Seoul"

DEFAULT_LEVERAGE = 4
DEFAULT_ENTRY_1_PCT = 0.02
DEFAULT_ENTRY_2_PCT = 0.01
DEFAULT_ENTRY_3_PCT = 0.01
DEFAULT_PUMP_THRESHOLD_PCT = 3.0

# 추가진입: 숏 기준 가격이 직전 진입가 대비 +5% 올라가면 다음 차수.
# 레버리지 4배 기준 약 -20% 손실 구간.
DEFAULT_ADD_ENTRY_PRICE_MOVE_PCT = 5.0

# 익절/손절: 레버리지 기준
DEFAULT_TAKE_PROFIT_LEVERAGED_PCT = 12.0
DEFAULT_STOP_LOSS_LEVERAGED_PCT = -30.0

BOT_VERSION = "FINAL v3.4"
