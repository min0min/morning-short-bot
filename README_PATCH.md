# v4.2 Auto BingX Listing Filter Patch

덮어쓸/추가 파일:
- config.py
- bingx.py
- scheduler.py
- messages.py
- telegram_bot.py

핵심 기능:
- 버전: FINAL v4.2 AUTO-BINGX-FILTER
- 수동 BingX 상장 체크 버튼 없이 자동으로 상장 여부 확인
- 09:15 전략 신호 발생 후 자동으로 BingX USDT-M 선물 상장 여부 확인
- BingX 상장 O → PAPER 진입 진행
- BingX 상장 X → 진입하지 않고 “BingX 선물 미상장 → 진입 없음” 알림
- BingX 상장 확인 오류 → 안전상 진입 보류
- “가상 수익 현황” → “수익 현황”
- “모의 시작/중지” → “트레이딩 시작/중지”

전략 기조 유지:
- Bitget 선물 전체 스캔
- 업비트 + 빗썸 교차상장 필터
- 09:15 마감 15분봉 O→C +3%
- 조건 충족 후보 중 상승률 1등만 선정
- BingX 상장된 경우만 진입 후보
- 현재 v4.2는 아직 실전 주문 없음, PAPER 진입만 수행
