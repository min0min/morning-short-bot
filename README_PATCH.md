# v2.3 Scheduler Debug Patch

덮어쓸 파일:
- main.py
- scheduler.py

추가:
- 서버 시작 시 텔레그램 알림
- 등록된 스케줄 Job 목록 출력
- 08:59 Scheduler Alive 알림
- 09:14 Scan Ready 알림
- 09:15 Scan Start 알림
- 09:15 스캔 결과/조건 없음/진입/에러 로그 강화
- Railway 로그에 KST 시간, Job next_run_time 출력
- misfire_grace_time=300 적용
