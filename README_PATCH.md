# v1.9 15m Backtest Patch

덮어쓸/추가할 파일:
- exchanges.py
- messages.py
- scheduler.py
- telegram_bot.py
- backtest.py

수정:
- 날짜 백테스트를 1분봉 기준이 아니라 15분봉 기준으로 변경
- 09:00~09:15 KST 15분봉 1개만 사용
- 기준가 = 15분봉 open
- 최고가 = 15분봉 high
- 09:15 가격 = 15분봉 close
- 최고 상승률 = (high - open) / open * 100

기존 실시간 자동 전략은 그대로 유지:
- 09:00 기준가 저장
- 09:00~09:15 30초마다 최고가 추적
- 09:15 +3% 이상 최상위 1종목 PAPER 숏 진입
