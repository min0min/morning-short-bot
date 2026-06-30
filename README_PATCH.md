# v3.3 Realtime/Backtest Unified Signal Fix

덮어쓸 파일:
- scanner.py
- backtest.py
- scheduler.py
- telegram_bot.py

핵심 수정:
- 실시간 스캔과 날짜 백테스트가 같은 select_signal_by_closed_15m() 함수만 사용
- 백테스트에서는 진입 종목이 나오는데 실시간에서는 signal=None 뜨는 불일치 방지
- 09:15:20 / 09:16:10 / 09:17:10 재시도 유지
- 스캔 로그에 passed_count, TOP1, SIGNAL 출력
- TOP20 브리핑은 top20만 출력하지만 signal은 전체 후보에서 선정
- ENTRY 직전 open_position 재확인으로 중복 진입 방지
