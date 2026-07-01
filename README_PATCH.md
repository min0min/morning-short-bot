# v4.3.3 BingX Fills + Fixed Leverage Patch

덮어쓸 파일:
- config.py
- bingx.py
- storage.py
- messages.py
- telegram_bot.py

핵심 반영:
- 버전: FINAL v4.3.3 FILLS-LEVERAGE
- 실전 레버리지 4배 고정 인지 및 반영
- 실전 주문 전 BingX 레버리지 4배 설정 시도
- 주문 성공 후 BingX 주문 상세/체결내역 조회
- 체결 평균가와 실제 체결수량 우선 저장
- 청산 후 BingX 체결/실현손익 데이터 우선 사용
- 거래소가 체결/실현손익을 반환하지 않는 경우에만 참고가 fallback
- 수익현황/거래내역에 체결 기반 값 반영

주의:
- BingX 계정 모드/엔드포인트 차이에 따라 레버리지 설정 API 또는 체결내역 API가 실패할 수 있습니다.
- 이 경우 주문 자체는 성공할 수 있으며, 봇은 가능한 데이터로 fallback합니다.
- Withdraw / Universal Transfer 권한은 계속 OFF 유지.
