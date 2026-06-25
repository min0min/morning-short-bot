# v1.8 Date Backtest Patch

덮어쓸/추가할 파일:
- exchanges.py
- messages.py
- scheduler.py
- telegram_bot.py
- backtest.py

추가 기능:
- 🧪 날짜 백테스트 버튼
- 날짜 입력 예: 2026-06-25
- 해당 날짜의 09:00~09:15 KST 구간을 Bitget 1분봉으로 재현
- 교차상장+비트겟 선물 종목 전체를 대상으로 최고 상승률 TOP20 출력
- 백테스트는 실제 PAPER 포지션을 만들지 않음

기존 실시간 자동 전략:
- 09:00 기준가 저장
- 09:00~09:15 30초마다 최고가 추적
- 09:15 +3% 이상 최상위 1종목 PAPER 숏 진입
