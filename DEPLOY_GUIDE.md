# Morning Short Paper Bot 배포 가이드

이 버전은 VSCode 없이도 Railway / Render 같은 곳에 바로 올릴 수 있게 만든 배포용 버전입니다.

## 1. 필요한 값

`.env.example`을 참고해서 아래 값이 필요합니다.

```env
TELEGRAM_BOT_TOKEN=텔레그램_봇토큰
TELEGRAM_CHAT_ID=내_채팅ID
PAPER_SEED_USDT=1000
MODE=PAPER
```

## 2. Railway 배포

1. Railway 접속
2. New Project
3. Deploy from GitHub repo 또는 Upload
4. 환경변수 Variables에 아래 값 추가

```env
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
PAPER_SEED_USDT=1000
MODE=PAPER
```

5. Deploy 실행

Railway는 `Dockerfile` 또는 `railway.json`을 보고 자동 실행합니다.

## 3. Render 배포

1. Render 접속
2. New → Background Worker
3. GitHub repo 연결
4. Build Command

```bash
pip install -r requirements.txt
```

5. Start Command

```bash
python main.py
```

6. 환경변수 등록 후 배포

## 4. 로컬 실행

```bash
pip install -r requirements.txt
cp .env.example .env
python main.py
```

## 5. 텔레그램 사용

봇에게 `/start` 입력하면 메뉴가 뜹니다.

## 6. 주의

현재 버전은 실주문 없는 PAPER MODE입니다.
실제 거래소 주문 API는 연결하지 않았습니다.
