# v4.5.1 Profit Display Hotfix

덮어쓸 파일:
- config.py
- telegram_bot.py
- messages.py

수정:
- 수익현황 버튼을 누르면 기존 메뉴 메시지를 수정하지 않고 새 메시지로 출력
- Telegram의 Message is not modified / 화면 미변경 문제 방지
- 기존 v4.5 관리자 승인 구조와 실전 전략 구조는 유지

전략 유지:
- 09:15 O→C +3%
- 교차상장
- BingX 상장 확인
- 4배 고정
- 1차 2%, 2차 1%, 3차 1%
- TP +12%
- 16시 이후 SL -30%, 미충족 시 계속 홀딩
