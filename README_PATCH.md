# v4.6.1 Send Main Menu Hotfix

덮어쓸 파일:
- config.py
- telegram_bot.py

수정:
- /start 실행 시 발생한 오류 수정
  NameError: name 'target_chat_id' is not defined
- 원인:
  send_main_menu() 내부에서 실제 변수명은 chat_id인데 target_chat_id를 호출함
- 조치:
  main_keyboard(chat_id)로 정확하게 수정

기존 v4.6.0 멀티유저 구조 유지:
- chat_id별 API/시드/승인/포지션/거래내역 독립 저장
- 관리자 전체 유저 모니터링
- 09:15 멀티유저 실전 전략 유지

전략 유지:
- 09:15 O→C +3%
- 업비트+빗썸 교차상장
- BingX 상장 확인
- 4배 고정
- 1차 2%, 2차 1%, 3차 1%
- TP +12%
- 16시 이후 SL -30%, 미충족 시 계속 홀딩
- 30초 감시 유지, TP 도달 시 자동 익절
