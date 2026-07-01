# v4.4 Live Strategy Engine Patch

덮어쓸/추가 파일:
- config.py
- storage.py
- messages.py
- telegram_bot.py
- scheduler.py

중요:
- 이 버전부터 09:15 전략 신호가 실전 BingX 주문으로 연결됩니다.
- 실전입니다. 반드시 BingX 포지션 화면을 같이 확인하세요.

핵심 반영:
- 버전: FINAL v4.4 LIVE-STRATEGY
- 레버리지 4배 고정
- 내 상태 UI 개선:
  - 거래소: BingX Futures
  - API 등록 여부
  - 트레이딩 활성화 여부
  - 시드 방식
  - 선물 잔고
  - 레버리지 4배 고정
  - 가입일
  - 오픈 포지션
- 수익 현황 UI 개선:
  - 총 누적 수익
  - 승률
  - 정산 완료/보유중
  - 이번 달/이번 주
  - 최고 거래/최대 손실
- 09:15 자동 실전 진입:
  - Bitget 선물 전체 스캔
  - 업비트 + 빗썸 교차상장
  - 마감 15분봉 O→C +3% 이상
  - Top1 선정
  - BingX 선물 상장 자동 확인
  - BingX 상장 O → SHORT 실전 진입
  - BingX 상장 X → 진입 없음
- 잔고 자동조회 기반 비중:
  - 1차 증거금: 선물 사용 가능 잔고의 2%
  - 2차 증거금: 1%
  - 3차 증거금: 1%
  - 주문가치 = 증거금 × 4배
- 30초 실전 포지션 감시
- TP: 레버리지 기준 +12%
- SL: 16:00 이후 레버리지 기준 -30%
- 추가진입: 불리하게 약 +3% 이동 시 2차/3차

주의:
- LIVE_STRATEGY_ENABLED=True 입니다.
- 트레이딩 시작 버튼을 누르면 다음 09:15부터 실전 진입 조건이 충족될 때 주문이 나갈 수 있습니다.
- API 권한: Read + Perpetual Futures Trading ON
- Withdraw / Universal Transfer OFF 필수
- 하루 1회 신규 진입 제한 적용
