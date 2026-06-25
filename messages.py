def fmt_usdt(x):
    return f"${float(x):,.2f}"

def main_menu_text():
    return "📌 메인 메뉴\n원하는 기능을 선택하세요."

def entry_message(pos, signal):
    e = pos["entries"][0]

    peak_info = ""
    if signal.get("baseline_price") is not None:
        peak_info = f"""
09:00 기준가 : {signal.get('baseline_price')}
15분 최고가 : {signal.get('peak_price')}
현재가 : {signal.get('price')}
현재 상승률 : +{signal.get('last_change_pct', 0):.2f}%"""

    return f"""🚨 [PAPER ENTRY]

종목 : {pos['base']}
심볼 : {pos['symbol']}

조건 충족
✅ 업비트 상장
✅ 빗썸 상장
✅ 비트겟 선물 가능
✅ 15분 최고 상승률 1위 (+{signal['change_pct']:.2f}%)
{peak_info}

------------------

가상 시드 : {fmt_usdt(pos['total_margin'] / 0.02)}

1차 진입 비중 : 2%
증거금 : {fmt_usdt(e['margin'])}

레버리지 : 4배
포지션 크기 : {fmt_usdt(e['notional'])}

진입가 : {e['price']}

TP : 레버리지 기준 +12%
SL 체크 : 16:00 이후 -30%

상태 : PAPER MODE"""

def add_message(entry, pos):
    return f"""⚠️ [PAPER ADD ENTRY]

종목 : {pos['base']}

{entry['level']}차 진입 실행

진입가 : {entry['price']}
추가 증거금 : {fmt_usdt(entry['margin'])}
추가 포지션 : {fmt_usdt(entry['notional'])}

현재 평균가 : {pos['avg_price']:.8f}
총 증거금 : {fmt_usdt(pos['total_margin'])}
총 포지션 : {fmt_usdt(pos['total_notional'])}

상태 : PAPER MODE"""

def close_message(pos, balance):
    emoji = "✅" if pos["close_reason"] == "TAKE_PROFIT" else "❌"
    title = "PAPER TAKE PROFIT" if pos["close_reason"] == "TAKE_PROFIT" else "PAPER STOP LOSS"

    return f"""{emoji} [{title}]

종목 : {pos['base']}

평균 진입가 : {pos['avg_price']:.8f}
청산가 : {pos['close_price']}

수익률 : {pos['pnl_pct']:.2f}%
실현손익 : {fmt_usdt(pos['realized_pnl'])}

가상 잔고 : {fmt_usdt(balance)}

상태 : PAPER MODE"""

def status_message(state):
    pos = state.get("open_position")
    if not pos:
        position_text = "없음"
    else:
        position_text = f"""{pos['base']} SHORT
평균가 : {pos['avg_price']:.8f}
총 증거금 : {fmt_usdt(pos['total_margin'])}
진입 차수 : {len(pos['entries'])}차"""

    return f"""📊 [내 상태]

모의 실행 : {'ON' if state['running'] else 'OFF'}
가상 시드 : {fmt_usdt(state['seed_usdt'])}
가상 잔고 : {fmt_usdt(state['paper_balance'])}

오픈 포지션 :
{position_text}"""

def scan_result_message(candidates, threshold, signal=None, include_below=True):
    """
    candidates: TOP 리스트. include_below=True면 +3% 미만도 포함된 전체 TOP.
    signal: 실제 진입 후보. +threshold 이상 중 1등. 없으면 None.
    """
    if not candidates:
        return f"""📭 [09:15 PEAK SCAN]

09:00~09:15 최고 상승률 기준
계산된 후보가 없습니다.

진입 없음"""

    top_lines = ""
    for i, c in enumerate(candidates[:10], 1):
        top_lines += (
            f"{i}. {c['base']} "
            f"최고 +{c['change_pct']:.2f}% "
            f"/ 현재 +{c.get('last_change_pct', 0):.2f}%
"
        )

    if signal:
        return f"""📈 [09:15 PEAK SCAN 결과]

09:00~09:15 최고 상승률 TOP10

{top_lines}

🎯 진입 조건 충족
기준 : +{threshold}% 이상

🏆 선정 종목
{signal['base']} / 최고 +{signal['change_pct']:.2f}%

이 종목만 PAPER 숏 진입합니다."""

    return f"""📭 [09:15 PEAK SCAN 결과]

09:00~09:15 최고 상승률 TOP10

{top_lines}

⚠️ 진입 조건 미충족
기준 : +{threshold}% 이상

+{threshold}% 이상 급등 종목 없음

진입 없음"""


def today_pump_test_message(candidates, threshold):
    if not candidates:
        return f"""📭 [오늘 급등 테스트]

비트겟 선물 현재 상승률 기준
업비트+빗썸 교차상장 종목 중
+{threshold}% 이상 급등 종목 없음"""

    top_lines = ""
    for i, c in enumerate(candidates[:20], 1):
        top_lines += f"{i}. {c['base']} +{c['change_pct']:.2f}% / 가격 {c['price']}\n"

    winner = candidates[0]
    return f"""🧪 [오늘 급등 테스트]

현재 비트겟 선물 상승률 기준
업비트+빗썸 교차상장 후보 TOP20

{top_lines}

🏆 선정 종목
{winner['base']} +{winner['change_pct']:.2f}%

PAPER 숏 진입 대상으로 선정합니다."""


def backtest_result_message(date_text, candidates, threshold, total_symbols, errors=0):
    if not candidates:
        return f"""🧪 [날짜 백테스트 결과]

날짜 : {date_text}
구간 : 09:00~09:15 KST
추적 종목 : {total_symbols}개
캔들 오류/누락 : {errors}개

+{threshold}% 이상 급등 종목 없음"""

    top_lines = ""
    for i, c in enumerate(candidates[:20], 1):
        top_lines += (
            f"{i}. {c['base']} "
            f"최고 +{c['change_pct']:.2f}% "
            f"/ 09:15 +{c.get('last_change_pct', 0):.2f}%\n"
        )

    winner = candidates[0]
    enter_text = (
        f"✅ 진입 조건 충족\n🏆 선정 종목 : {winner['base']} +{winner['change_pct']:.2f}%"
        if winner["change_pct"] >= threshold
        else f"⚠️ 진입 조건 미충족\n최고 종목 : {winner['base']} +{winner['change_pct']:.2f}%"
    )

    return f"""🧪 [날짜 백테스트 결과]

날짜 : {date_text}
구간 : 09:00~09:15 KST
추적 종목 : {total_symbols}개
캔들 오류/누락 : {errors}개

09:00~09:15 최고 상승률 TOP20

{top_lines}

{enter_text}

※ 백테스트는 실제 PAPER 포지션을 만들지 않습니다."""
