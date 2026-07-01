# v4.6.0 True Multiuser Patch

덮어쓸/추가 파일:
- config.py
- storage.py
- telegram_bot.py
- messages.py
- scheduler.py

핵심:
- chat_id별 독립 유저 저장소 도입: data/users.json
- 각 유저별로 API / 시드 / 승인 상태 / 트레이딩 ON-OFF / 포지션 / 거래내역 / 신호기록 분리
- 친구 2명이 API를 등록해도 서로 덮어쓰지 않음
- 관리자는 전체 유저를 한 화면에서 모니터링
- 09:15 전략 신호 발생 시 승인 + 트레이딩 ON 유저들에게 각각 독립 주문
- 30초 포지션 감시도 유저별 독립 수행
- 16:00 SL 체크도 유저별 독립 수행

관리자:
- ADMIN_CHAT_ID와 일치하는 계정만 👑 관리자 버튼 표시
- 관리자 대시보드에서 전체 유저:
  - chat_id
  - 승인 상태
  - API 등록 여부
  - 시드 방식
  - BingX 선물 잔고
  - 현재 포지션
  - 손익/승률
  모니터링 가능
- 전체 강제 중지 버튼 제공

전략 유지:
- 09:15 마감 15분봉 O→C +3%
- 업비트+빗썸 교차상장
- BingX 선물 상장 확인
- 레버리지 4배 고정
- 1차 2%, 2차 1%, 3차 1%
- 주문가치 = 증거금 × 4배
- TP +12%
- 16시 이후 SL -30%
- -30% 미충족 시 계속 홀딩
- 30초 감시 유지, TP 도달 시 자동 익절

주의:
- 기존 단일 state.json/bingx_api.json/trades.json은 첫 실행 시 users.json으로 자동 마이그레이션 시도
- 이후부터는 users.json이 기준
- Railway 변수 ADMIN_CHAT_ID=1529816817 필수 권장
