# v4.4.1 Import Hotfix + Strategy Keep

덮어쓸 파일:
- config.py
- bingx.py
- scheduler.py

수정 내용:
- ImportError 수정:
  cannot import name 'place_short_market_order_with_leverage' from 'bingx'
- v4.3.3에서 쓰던 레버리지/체결내역 wrapper 함수들을 bingx.py에 복구
- 전략 유지:
  - 레버리지 4배 고정
  - 09:15 마감 15분봉 O→C +3%
  - 업비트+빗썸 교차상장
  - BingX 상장 O일 때 실전 SHORT
  - 1차 2%, 2차 1%, 3차 1%
  - TP 레버리지 기준 +12%
  - 16:00 이후 SL -30% 체크
  - -30% 미충족 시 손절하지 않고 계속 홀딩
  - 이후에도 30초 감시 유지, TP 도달 시 자동 익절

중요:
- 이번 패치는 크래시 핫픽스입니다.
- 반드시 config.py, bingx.py, scheduler.py를 함께 덮어쓰기하세요.
