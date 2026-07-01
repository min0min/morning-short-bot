# v4.0 BingX Read API + Seed Auto Patch

덮어쓸/추가 파일:
- config.py
- storage.py
- messages.py
- telegram_bot.py
- bingx.py

기능:
- BingX API 등록 안내/동의 문구 추가
- API Key / Secret 입력 플로우
- 입력 메시지 삭제 시도
- BingX Read API 연결 테스트
- USDT 선물 잔고 조회
- 포지션 조회 개수 표시
- 시드 설정에서 0 입력 시 BingX 사용 가능 잔고 자동 조회
- 이후 자동조회 모드(seed_mode=auto) 저장
- 고정 시드와 자동조회 시드 구분
- 상태 화면에 거래소/API/시드 방식 표시

주의:
- v4.0은 주문 기능 없음
- BingX API 권한은 Read만 사용
- Perpetual Futures Trading 권한은 실전 주문 단계(v4.3 이후)에만 추가 권장
