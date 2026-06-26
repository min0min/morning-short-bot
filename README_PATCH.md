# v3.2 State Chat ID Only Patch

덮어쓸 파일:
- storage.py
- telegram_bot.py
- scheduler.py
- main.py

핵심 변경:
- /start를 한 번이라도 누르면 해당 chat_id를 state.json에 저장
- 버튼 클릭/텍스트 입력 때도 chat_id 자동 갱신
- 이후 모든 스케줄 알림은 state.json의 active_chat_id만 사용
- TELEGRAM_CHAT_ID 환경변수로 메시지 보내지 않음
- Chat not found 방지 강화

적용 후:
1. 덮어쓰기
2. Redeploy
3. 텔레그램에서 /start
4. 모의 시작 ON 확인
5. Railway 로그에 [CHAT ID SAVED]가 뜨는지 확인
