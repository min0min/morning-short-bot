# v4.5 Profit Fix + Admin Approval Patch

덮어쓸/추가 파일:
- config.py
- storage.py
- messages.py
- telegram_bot.py
- scheduler.py

핵심 수정:
- 수익현황 버튼이 화면을 바꾸지 않던 오류 수정
  - get_real_test_stats, get_live_trade_stats 튜플 호출 버그 제거
  - live_profit_message(get_live_trade_stats())로 정상 출력
- 관리자 승인 구조 1차 구현
  - ADMIN_CHAT_ID 추가
  - API/시드 설정 후 승인 대기 상태
  - 관리자에게 승인 요청 메시지 전송
  - [승인] [거절] [보류/일시정지] 버튼
  - 승인 전 트레이딩 시작 차단
  - 승인 전 09:15 실전 주문 이중 차단
- 기존 전략 유지
  - 09:15 마감 15분봉 O→C +3%
  - 업비트+빗썸 교차상장
  - BingX 상장 자동 확인
  - 레버리지 4배 고정
  - 1차 2%, 2차 1%, 3차 1%
  - TP +12%
  - 16:00 이후 SL -30%
  - -30% 미충족 시 계속 홀딩, TP 도달 시 자동 익절

Railway 변수:
- ADMIN_CHAT_ID 추가 권장
- 값은 관리자 텔레그램 chat_id
- 비워두면 TELEGRAM_CHAT_ID를 관리자 ID로 사용
