# v4.3.1 BingX Order Rules Patch

덮어쓸 파일:
- config.py
- bingx.py
- messages.py
- telegram_bot.py

핵심 수정:
- 버전: FINAL v4.3.1 ORDER-RULES
- 1 USDT 테스트 주문이어도 BingX 거래소 최소 주문 규칙에 맞게 수량 자동 보정
- BingX contract rule 조회:
  - minQty / quantityPrecision / stepSize / minNotional 계열 자동 탐색
- 주문 전:
  - 요청 수량
  - 최소 수량
  - 실제 주문 수량
  - 예상 주문금액
  계산
- BingX가 "minimum order amount is 28 DOGE" 같은 오류를 반환하면 숫자를 파싱해서 1회 자동 재시도
- 주문 성공 메시지에 거래소 규칙 보정 여부 표시

중요:
- 실제 주문입니다.
- 요청 금액은 1 USDT여도, 거래소 최소 주문 수량 때문에 실제 주문금액은 1 USDT보다 커질 수 있습니다.
- Withdraw / Transfer 권한은 절대 OFF 유지.
