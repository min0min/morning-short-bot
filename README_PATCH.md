# v4.1 BingX Listing Check + Label Rename Patch

덮어쓸/추가 파일:
- config.py
- bingx.py
- telegram_bot.py
- messages.py

기능:
- 버전: FINAL v4.1 BINGX-LISTING
- "가상 수익 현황" → "수익 현황" 문구 변경
- 메인 메뉴에 "🔎 BingX 상장 체크" 버튼 추가
- 종목 입력 시 BingX USDT-M 선물 상장 여부 확인
- 상장 O: 실전 주문 후보 가능 문구 출력
- 상장 X: 전략 신호가 떠도 실전 진입 없음 문구 출력

전략 기조 유지:
- Bitget 선물 스캔
- 업비트+빗썸 교차상장 필터
- 09:15 마감 15분봉 O→C +3%
- 1등 종목 선정
- 다음 단계에서 BingX 상장 O일 때만 실전 주문 연결
