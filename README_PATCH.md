# v2.2 Stats + Excursion Patch

덮어쓸/추가할 파일:
- storage.py
- strategy.py
- messages.py
- scheduler.py
- telegram_bot.py

추가 기능:
1순위: 승률 통계
- 📈 신호 통계 버튼 작동
- 청산 완료 거래 기준 승/패/승률/누적손익/평균손익/최대연승/최대연패/최고거래/최악거래 표시

2순위: 진입 후 최대 유리/불리 구간 추적
- 오픈 포지션 감시 중 30초마다 현재 수익률 갱신
- 최대 유리 수익률(max_pnl_pct)
- 최대 불리 수익률(min_pnl_pct)
- 청산 메시지와 상태 화면에 표시

기존 v2.1 전략 유지:
- Bitget 마감 15분봉 O→C 기준
- 업비트+빗썸 교차상장
- +3% 이상 1등만 PAPER 숏 진입
