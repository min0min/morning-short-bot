# v2.1 Closed 15m Candle Strategy Patch

덮어쓸/추가할 파일:
- exchanges.py
- messages.py
- scheduler.py
- telegram_bot.py
- backtest.py
- scanner.py

핵심:
- 알림봇과 동일한 기준으로 재정렬
- 09:00에 시작해 09:15에 마감된 Bitget 선물 15분봉 사용
- 상승률 = (Close - Open) / Open * 100
- 업비트 + 빗썸 교차상장 + Bitget 선물 가능 종목만 대상
- +3% 이상 후보 중 O→C 상승률 1등만 PAPER 숏 진입

실시간:
- 매일 09:15에 방금 마감된 15분봉으로 자동 스캔

테스트:
- 🧪 마감 15분봉 즉시 테스트
- 🧪 날짜 백테스트
- 🧪 최근 7일 자동 검증
