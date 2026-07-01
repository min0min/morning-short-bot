# v4.5.3 Profit Tuple Error Fix

덮어쓸 파일:
- config.py
- telegram_bot.py
- messages.py
- storage.py

수정:
- 수익현황 클릭 시 발생한 오류 수정
  AttributeError: 'tuple' object has no attribute 'get'
- 원인:
  과거 콜백에 stats = get_real_test_stats, get_live_trade_stats() 형태가 남아 tuple이 전달됨
- 조치:
  telegram_bot.py profit callback 강제 재작성
  live_profit_message()에 tuple 방어 로직 추가
  수익현황은 트레이딩 시작 여부와 무관하게 새 메시지로 출력

기존 전략 유지:
- 09:15 O→C +3%
- 업비트+빗썸 교차상장
- BingX 상장 확인
- 4배 고정
- 1차 2%, 2차 1%, 3차 1%
- TP +12%
- 16시 이후 SL -30%, 미충족 시 계속 홀딩
- 관리자 승인 구조 유지
