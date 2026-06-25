# v2.0 Final O→C Strategy Patch

덮어쓸/추가할 파일:
- storage.py
- exchanges.py
- messages.py
- scheduler.py
- telegram_bot.py
- backtest.py

핵심 수정:
- 기존 high 기준 제거
- 알림봇과 동일하게 15분봉 O→C 기준으로 변경
- 상승률 = (Close - Open) / Open * 100
- High는 참고용으로만 출력
- 실시간 자동 전략:
  - 09:00 기준가 저장
  - 09:00~09:15 현재가 업데이트
  - 09:15 마지막 가격 기준 O→C 상승률 계산
  - +3% 이상 후보 중 TOP1만 PAPER 숏 진입
- 날짜 백테스트:
  - 09:00~09:15 KST 15분봉 O→C 기준
- 추가 기능:
  - 🧪 최근 7일 자동 검증
