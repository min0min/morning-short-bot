# v3.5 Communication Stability Patch

덮어쓸 파일:
- config.py
- storage.py
- telegram_bot.py
- scheduler.py
- main.py

핵심:
- BOT_VERSION = FINAL v3.5 COMM-STABLE
- 시작 메시지는 active_chat_id가 있을 때만 전송
- active_chat_id가 없으면 BadRequest 없이 안전하게 스킵
- /start 입력 시 active_chat_id 저장 + 텔레그램에 저장 완료 출력
- callback/text 입력 시에도 active_chat_id 갱신
- 모든 스케줄러 알림은 active_chat_id 우선 사용
- ENV TELEGRAM_CHAT_ID는 fallback으로만 사용
- 로그에 CHAT SOURCE 출력
- 기존 전략/스케줄 유지:
  - 09:15:20 PRIMARY
  - 09:16:10 RETRY_1
  - 09:17:10 FINAL_RETRY
  - 30초 포지션 감시
  - 16:00 SL 체크

배포 후 확인:
1. Railway 로그에 FINAL v3.5 COMM-STABLE started 표시
2. Telegram에서 /start
3. "CHAT ID 저장 완료 / 버전 FINAL v3.5 COMM-STABLE" 메시지 확인
4. Railway 로그에 [CHAT ID SAVED] 확인
