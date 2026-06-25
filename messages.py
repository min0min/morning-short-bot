def fmt_usdt(x):
    return f"${float(x):,.2f}"

def main_menu_text():
    return "📌 메인 메뉴\n원하는 기능을 선택하세요."

def entry_message(pos, signal):
    e = pos["entries"][0]
    peak_info = ""
    if signal.get("peak_price") is not None:
        peak_info = f"\n09:00 기준가 : {signal.get('baseline_price')}\n15분 최고가 : {signal.get('peak_price')}\n현재가 : {signal.get('price')}\n"

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

def scan_result_message(candidates, threshold):
    if not candidates:
        return f"""📭 [09:15 PEAK SCAN]

09:00~09:15 최고 상승률 기준
+{threshold}% 이상 급등 종목 없음

진입 없음"""

    top_lines = ""
    for i, c in enumerate(candidates[:20], 1):
        top_lines += (
            f"{i}. {c['base']} "
            f"최고 +{c['change_pct']:.2f}% "
            f"/ 현재 +{c.get('last_change_pct', 0):.2f}%\n"
        )

    winner = candidates[0]
    return f"""📈 [09:15 PEAK SCAN 결과]

09:00~09:15 동안
최고 상승률 기준 TOP 후보

{top_lines}

🎯 선정 종목
{winner['base']} / 최고 +{winner['change_pct']:.2f}%

이 종목만 PAPER 숏 진입합니다."""
