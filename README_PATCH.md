# v1.7 TOP10 Debug Patch

덮어쓸 파일:
- messages.py
- scheduler.py
- telegram_bot.py

변경:
- +3% 이상 종목이 없어도 09:15 PEAK SCAN에서 TOP10을 항상 출력
- 실제 진입은 기존처럼 +3% 이상 후보 중 1등만 진입
- +3% 미만이면 진입 없음
