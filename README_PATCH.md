# v3.4 Active Chat ID + Version Fix

덮어쓸 파일:
- config.py
- storage.py
- telegram_bot.py
- scheduler.py
- main.py

핵심 수정:
- /start 입력 시 현재 chat_id를 data/active_chat.json에 저장
- 저장 성공 시 텔레그램에 "CHAT ID 저장 완료" 표시
- Railway 로그에 [CHAT ID SAVED] 출력
- 스케줄러 알림은 저장된 active_chat_id를 최우선 사용
- active_chat_id가 없을 때만 TELEGRAM_CHAT_ID 사용
- BOT_VERSION = FINAL v3.4 추가
- 시작 로그/텔레그램 시작 메시지에 정확한 버전 표시
- v3.3 재시도 구조 유지:
  09:15:20 PRIMARY
  09:16:10 RETRY_1
  09:17:10 FINAL_RETRY
