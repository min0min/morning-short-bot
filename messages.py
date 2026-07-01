def fmt_usdt(x):
    return f"${float(x):,.2f}"

def main_menu_text():
    return "📌 메인 메뉴\n원하는 기능을 선택하세요."

def entry_message(pos, signal):
    e = pos["entries"][0]
    candle_info = ""
    if signal.get("baseline_price") is not None:
        candle_info = (
            f"\n15분봉 O : {signal.get('baseline_price')}"
            f"\n15분봉 C : {signal.get('price')}"
            f"\n15분봉 H : {signal.get('peak_price')}"
            f"\nO→C 상승률 : +{signal.get('change_pct', 0):.2f}%"
            f"\nH 참고 상승률 : +{signal.get('peak_change_pct', 0):.2f}%"
        )

    return f"""🚨 [PAPER ENTRY]

종목 : {pos['base']}
심볼 : {pos['symbol']}

조건 충족
✅ 업비트 상장
✅ 빗썸 상장
✅ 비트겟 선물 가능
✅ 마감 15분봉 O→C 상승률 1위 (+{signal['change_pct']:.2f}%)
{candle_info}

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

최대 유리 : {pos.get('max_pnl_pct', 0):.2f}% @ {pos.get('max_pnl_price', '-')}
최대 불리 : {pos.get('min_pnl_pct', 0):.2f}% @ {pos.get('min_pnl_price', '-')}

상태 : PAPER MODE"""

def status_message(state):
    pos = state.get("open_position")
    if not pos:
        position_text = "없음"
    else:
        position_text = f"""{pos['base']} SHORT
평균가 : {pos['avg_price']:.8f}
총 증거금 : {fmt_usdt(pos['total_margin'])}
진입 차수 : {len(pos['entries'])}차
현재 수익률 : {pos.get('last_pnl_pct', 0):.2f}%
최대 유리 : {pos.get('max_pnl_pct', 0):.2f}%
최대 불리 : {pos.get('min_pnl_pct', 0):.2f}%"""

    return f"""📊 [내 상태]

트레이딩 실행 : {'ON' if state['running'] else 'OFF'}
가상 시드 : {fmt_usdt(state['seed_usdt'])}
가상 잔고 : {fmt_usdt(state['paper_balance'])}

오픈 포지션 :
{position_text}"""

def scan_result_message(candidates, threshold, signal=None, total_symbols=None, errors=0, title="09:15 마감봉 SCAN"):
    if not candidates:
        return f"""📭 [{title}]

마감 15분봉 O→C 기준
계산된 후보가 없습니다.

진입 없음"""

    top_lines = ""
    for i, c in enumerate(candidates[:20], 1):
        top_lines += (
            f"{i}. {c['base']} "
            f"O→C +{c['change_pct']:.2f}% "
            f"/ H참고 +{c.get('peak_change_pct', 0):.2f}%\n"
        )

    meta = ""
    if total_symbols is not None:
        meta = f"추적 종목 : {total_symbols}개\n캔들 오류/누락 : {errors}개\n\n"

    if signal:
        return f"""📈 [{title} 결과]

{meta}마감 15분봉 O→C 상승률 TOP20

{top_lines}

🎯 진입 조건 충족
기준 : O→C +{threshold}% 이상

🏆 선정 종목
{signal['base']} / O→C +{signal['change_pct']:.2f}%

이 종목만 PAPER 숏 진입합니다."""

    return f"""📭 [{title} 결과]

{meta}마감 15분봉 O→C 상승률 TOP20

{top_lines}

⚠️ 진입 조건 미충족
기준 : O→C +{threshold}% 이상

진입 없음"""

def backtest_result_message(date_text, candidates, threshold, total_symbols, errors=0):
    title = f"날짜 백테스트 {date_text}"
    signal = candidates[0] if candidates and candidates[0]["change_pct"] >= threshold else None
    msg = scan_result_message(
        candidates,
        threshold,
        signal=signal,
        total_symbols=total_symbols,
        errors=errors,
        title=title,
    )
    return msg + "\n\n※ 백테스트는 실제 PAPER 포지션을 만들지 않습니다."

def weekly_backtest_result_message(results, threshold):
    lines = ""
    total_days = 0
    signal_days = 0

    for r in results:
        total_days += 1
        date_text = r["date"]
        candidates = r.get("candidates", [])
        errors = r.get("errors", 0)
        total_symbols = r.get("total_symbols", 0)

        if not candidates:
            lines += f"{date_text} : 후보 없음 / 추적 {total_symbols} / 오류 {errors}\n"
            continue

        winner = candidates[0]
        passed = winner["change_pct"] >= threshold
        if passed:
            signal_days += 1
            mark = "✅"
        else:
            mark = "⚠️"

        lines += f"{mark} {date_text} : {winner['base']} O→C +{winner['change_pct']:.2f}% / H +{winner.get('peak_change_pct', 0):.2f}%\n"

    return f"""🧪 [최근 7일 자동 검증]

기준 : 09:00~09:15 KST 마감 15분봉 O→C
진입 기준 : +{threshold}% 이상

검증일 : {total_days}일
진입 조건 충족일 : {signal_days}일

{lines}

※ 이 검증은 진입 종목 선정만 확인합니다."""

def stats_message(stats):
    best = stats.get("best")
    worst = stats.get("worst")

    best_text = "없음"
    if best:
        best_text = f"{best.get('base')} {best.get('pnl_pct'):.2f}% / ${best.get('pnl'):.2f}"

    worst_text = "없음"
    if worst:
        worst_text = f"{worst.get('base')} {worst.get('pnl_pct'):.2f}% / ${worst.get('pnl'):.2f}"

    return f"""📈 [신호 통계]

청산 완료 거래 : {stats['total']}회

승 : {stats['wins']}회
패 : {stats['losses']}회
승률 : {stats['win_rate']:.2f}%

누적 손익 : ${stats['total_pnl']:.2f}
평균 손익 : ${stats['avg_pnl']:.2f}

최대 연승 : {stats['max_win_streak']}회
최대 연패 : {stats['max_loss_streak']}회

최고 거래 : {best_text}
최악 거래 : {worst_text}"""


def api_register_guide_message():
    return """🔐 BingX API 등록 안내

본 봇은 자동매매 및 리스크 관리를 위해 API를 사용합니다.

사용 목적:
✅ 잔고 조회
✅ 포지션 조회
✅ 손익/거래내역 조회
✅ 실전 모드 승인 후 주문 실행

사용하지 않는 기능:
❌ 출금
❌ 자산 이동
❌ 계정 정보 변경

입력한 API 메시지는 등록 후 즉시 삭제를 시도합니다.
출금 권한이 없는 API 사용을 권장합니다.

동의하시나요?"""

def seed_setting_message():
    return """💰 시드 설정

사용할 기준 시드를 입력하세요.

예)
1000 → 1,000 USDT 고정 기준으로 비중 계산
0 → BingX 사용 가능 잔고를 매번 자동 조회하여 비중 계산

현재 전략:
1차 2%
2차 1%
3차 1%

❌ 취소하려면 /start"""

def bingx_connection_success_message(available_usdt, positions_count=0):
    return f"""✅ BingX API 연결 테스트 완료

잔고 조회 : 성공
사용 가능 USDT : ${available_usdt:,.2f}
오픈 포지션 수 : {positions_count}개

이제 시드 설정을 진행해주세요.
0 입력 시 이 잔고를 자동 조회 기준으로 사용합니다."""

def bingx_connection_fail_message(error):
    return f"""❌ BingX API 연결 테스트 실패

{error}

확인할 것:
1. API Key / Secret 오타
2. Read 권한 체크 여부
3. Perpetual Futures 계정 접근 가능 여부
4. IP 제한 설정 여부"""


def bingx_auto_listing_ok_message(signal, listing):
    base = signal.get("base")
    bx_symbol = listing.get("raw_symbol") or listing.get("symbol")
    return f"""✅ BingX 선물 상장 확인

선정 종목 : {base}
BingX 심볼 : {bx_symbol}

상태 : 상장됨
PAPER 진입을 진행합니다.

※ 현재 버전은 실전 주문이 아니라 PAPER 진입 단계입니다."""

def bingx_auto_listing_skip_message(signal, listing):
    base = signal.get("base")
    bx_symbol = listing.get("symbol") or f"{base}-USDT"
    oc = float(signal.get("change_pct", 0))
    return f"""❌ BingX 선물 미상장 → 진입 없음

선정 종목 : {base}
예상 BingX 심볼 : {bx_symbol}

09:15 전략 조건은 충족했지만,
BingX USDT-M 선물에 존재하지 않는 종목이라 주문하지 않습니다.

조건:
✅ Bitget 선물 감지
✅ 업비트+빗썸 교차상장
✅ 15분봉 O→C +{oc:.2f}%
❌ BingX 선물 미상장

결론 : 진입 없음"""

def bingx_auto_listing_error_message(signal, error):
    base = signal.get("base")
    return f"""⚠️ BingX 상장 확인 실패 → 안전상 진입 보류

선정 종목 : {base}

BingX 상장 여부 확인 중 오류가 발생했습니다.
실전 안정성을 위해 이번 신호는 진입하지 않습니다.

오류:
{error}"""
