# v3.1 Auto Chat ID Patch

덮어쓸 파일:
- storage.py
- telegram_bot.py
- scheduler.py
- main.py

수정 내용:
- /start 누른 최신 채팅방 chat_id를 자동 저장
- 버튼 클릭/메시지 입력 시에도 chat_id 자동 갱신
- TELEGRAM_CHAT_ID 환경변수가 틀려도 저장된 active_chat_id로 스케줄 알림 전송
- BadRequest: Chat not found 문제 방지
- 기존 전략/백테스트/최근 7일/통계/TP/SL/스케줄러 디버그는 그대로 유지

적용 후:
1. 덮어쓰기
2. Redeploy
3. 텔레그램에서 /start
4. 모의 시작 ON
5. Railway 로그에 Conflict/Chat not found가 사라지는지 확인
