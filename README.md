# Morning Short Paper Bot FINAL v3.0

## 최종 전략

- Bitget USDT 선물 전 종목 조회
- 업비트 KRW + 빗썸 KRW 교차상장 여부 확인
- 09:15 KST에 방금 마감된 15분봉 사용
- 09:00~09:15 15분봉 기준
- 상승률 = (Close - Open) / Open × 100
- +3% 이상 후보만 필터
- 후보 중 O→C 상승률 1등 1종목만 PAPER 숏 진입

## 리스크/청산

- 가상 시드 기본값: 1000 USDT
- 1차 진입: 시드 2%
- 2차 진입: 직전 진입가 대비 +5% 상승 시 시드 1%
- 3차 진입: 직전 진입가 대비 +5% 상승 시 시드 1%
- 레버리지: 4배
- 익절: 레버리지 기준 +12% 전량 청산
- 손절: 16:00 이후 레버리지 기준 -30% 이하이면 전량 손절

## 자동 알림

- 서버 시작 시 BOT STARTED
- 08:59 Scheduler Alive
- 09:14 Scan Ready
- 09:15 Scan Start
- 09:15 스캔 결과 TOP20
- 진입 시 PAPER ENTRY
- 청산 시 PAPER EXIT
- 16:00 손절 체크

## 테스트 기능

- 마감 15분봉 즉시 테스트
- 날짜 백테스트
- 최근 7일 자동 검증
- 거래소 디버그
- 신호 통계

## Railway Variables

```env
TELEGRAM_BOT_TOKEN=봇토큰
TELEGRAM_CHAT_ID=채팅ID
PAPER_SEED_USDT=1000
MODE=PAPER
```

## 배포 후 확인

1. Railway Deploy Logs에서 `Morning Short Paper Bot FINAL v3.0 started.` 확인
2. 텔레그램에 `BOT STARTED` 메시지 확인
3. `/start`
4. `내 상태`에서 모의 실행 ON 확인
5. 다음날 08:59 / 09:14 / 09:15 알림 확인
