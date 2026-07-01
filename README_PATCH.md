# v4.3 Real Order Test Engine Patch

덮어쓸/추가 파일:
- config.py
- bingx.py
- telegram_bot.py
- messages.py

핵심 기능:
- 버전: FINAL v4.3 REAL-ORDER-TEST
- 실전 주문 테스트 버튼 추가
- 실전 테스트 청산 버튼 추가
- 기본 테스트 심볼: DOGE-USDT
- 기본 테스트 금액: 1 USDT
- 실제 BingX Futures Market SHORT 주문 전송
- 현재 SHORT 포지션 조회 후 Market BUY 청산 테스트

중요:
- 이 버전은 전략 자동 실전 진입이 아님
- 버튼을 눌러 확인한 경우에만 실제 주문 시도
- BingX API에 Perpetual Futures Trading 권한이 필요
- Withdraw / Transfer 권한은 절대 켜지 말 것
- 최초 테스트는 반드시 1 USDT 수준으로만 진행

다음 단계:
- 주문 성공 확인
- 포지션 생성 확인
- 청산 성공 확인
- 거래내역 저장/실전 TP/SL 연결
- 이후 09:15 전략 자동 실전 주문 연결
