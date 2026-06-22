# Morning Short Paper Bot v1.0

09:15 국내 교차상장 급등 1등 종목 숏 모의투자 봇.

## 실행
```bash
pip install -r requirements.txt
cp .env.example .env
python main.py
```

## 핵심 전략
- 09:15 KST 실행
- 업비트 + 빗썸 교차상장
- 비트겟 선물 가능
- +3% 이상 급등 종목 중 상승률 1등 1개만 선택
- PAPER 숏 진입
- 1차 2%, 2차 1%, 3차 1%
- 2차: 1차 대비 +5%
- 3차: 2차 대비 +5%
- TP: 레버리지 기준 +12% 전량청산
- SL: 16:00 이후 -30% 이하일 때 전량청산
