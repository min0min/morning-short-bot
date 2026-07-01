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

def status_message(state, live_balance=None):
    pos = state.get("live_position") or state.get("open_position")
    if not pos:
        position_text = "없음"
    else:
        entries = pos.get("entries", [])
        position_text = f"""{pos.get('base')} SHORT
평균가 : {float(pos.get('avg_price', 0) or 0):.8f}
수량 : {float(pos.get('qty', 0) or 0):,.6f}
진입 차수 : {len(entries)}차
현재 수익률 : {float(pos.get('last_pnl_pct', 0) or 0):+.2f}%
최대 유리 : {float(pos.get('max_pnl_pct', 0) or 0):+.2f}%
최대 불리 : {float(pos.get('min_pnl_pct', 0) or 0):+.2f}%"""

    seed_mode = "자동 조회" if state.get("seed_mode") == "auto" else "고정"
    seed_text = "자동 조회" if state.get("seed_mode") == "auto" else fmt_usdt(state.get("seed_usdt", 0))
    balance_text = f"{float(live_balance):,.2f} USDT" if live_balance is not None else "조회 전"

    return f"""📊 [내 상태]

• 거래소: BingX Futures
• API: {'✅ 등록됨' if state.get('api_registered') else '❌ 미등록'}
• 트레이딩: {'▶️ 활성화' if state.get('running') else '⏸ OFF'}
• 시드: {seed_text}
• 시드 방식: {seed_mode}
• 선물 잔고: {balance_text}
• 레버리지: 4배 고정
• 전략: Morning Short
• 가입일: {state.get('joined_at') or '-'}

오픈 포지션:
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


def real_order_test_warning_message(symbol="DOGE-USDT", margin_usdt=1.0):
    return f"""🧪 실전 주문 테스트

이 기능은 실제 BingX Futures 계정에 주문을 넣습니다.

테스트 내용:
거래소 : BingX Futures
심볼 : {symbol}
방향 : SHORT
주문 방식 : Market
요청 금액 : 약 ${margin_usdt:.2f}\n※ 거래소 최소 주문 수량에 맞춰 실제 주문금액은 자동 보정될 수 있습니다.

주의:
✅ 실전 주문입니다.
✅ 수수료/슬리피지가 발생할 수 있습니다.
✅ Trade 권한이 켜진 API가 필요합니다.
❌ 자동 전략 진입은 아직 연결하지 않습니다.

진행하시겠습니까?"""

def real_order_success_message(result):
    raw = result.get("raw", {})
    order_id = "-"
    data = raw.get("data")
    if isinstance(data, dict):
        order_id = data.get("orderId") or data.get("orderID") or data.get("id") or "-"

    adjusted_text = "아니오"
    if result.get("adjusted"):
        adjusted_text = "예"

    rule = result.get("rule", {})
    min_qty = rule.get("min_qty")
    min_notional = rule.get("min_notional")

    return f"""✅ 실전 테스트 주문 성공

거래소 : BingX Futures
동작 : SHORT 진입
심볼 : {result.get('symbol')}

요청 금액 : ${float(result.get('margin_usdt', 0)):,.2f}
참고 가격 : {result.get('price_ref')}

요청 수량 : {float(result.get('requested_qty', 0)):,.6f}
실제 주문 수량 : {result.get('qty')}
예상 주문금액 : ${float(result.get('actual_notional_usdt', 0)):,.2f}

거래소 규칙 자동보정 : {adjusted_text}
최소 수량 : {min_qty if min_qty else '거래소 응답 기준'}
최소 금액 : {min_notional if min_notional else '거래소 응답 기준'}

Order ID : {order_id}

다음 단계:
🧪 실전 테스트 청산 버튼으로 포지션 청산을 확인하세요."""


def real_order_fail_message(error):
    return f"""❌ 실전 테스트 주문 실패

{error}

확인할 것:
1. BingX API에 Perpetual Futures Trading 권한이 켜져 있는지
2. 출금 권한은 꺼져 있는지
3. Futures 계정에 사용 가능 USDT가 있는지
4. 거래소 최소 주문 수량/금액 규칙 확인"""

def real_close_success_message(result):
    raw = result.get("raw", {})
    order_id = "-"
    data = raw.get("data")
    if isinstance(data, dict):
        order_id = data.get("orderId") or data.get("orderID") or data.get("id") or "-"
    return f"""✅ 실전 테스트 청산 성공

거래소 : BingX Futures
동작 : SHORT 청산
심볼 : {result.get('symbol')}
청산 수량 : {result.get('qty')}

Order ID : {order_id}

실전 주문 엔진 1차 테스트 완료."""

def real_close_fail_message(error):
    return f"""❌ 실전 테스트 청산 실패

{error}

포지션이 남아있다면 BingX 앱에서 직접 확인 후 수동 청산하세요."""


def real_close_success_message_with_pnl(result, closed_pos):
    raw = result.get("raw", {})
    order_id = "-"
    data = raw.get("data")
    if isinstance(data, dict):
        order_id = data.get("orderId") or data.get("orderID") or data.get("id") or "-"

    pnl = float(closed_pos.get("realized_pnl", 0) or 0)
    pnl_pct = float(closed_pos.get("pnl_pct", 0) or 0)
    close_price = closed_pos.get("close_price") or "-"

    return f"""✅ 실전 테스트 청산 성공

거래소 : BingX Futures
동작 : SHORT 청산
심볼 : {result.get('symbol')}
청산 수량 : {result.get('qty')}
청산 참고가 : {close_price}

추정 실현손익 : ${pnl:,.4f}
추정 수익률 : {pnl_pct:+.4f}%

Order ID : {order_id}

실전 주문 엔진 1차 테스트 완료.
거래내역/수익현황에 반영했습니다."""

def real_test_stats_message(stats):
    total = int(stats.get("total", 0))
    wins = int(stats.get("wins", 0))
    losses = int(stats.get("losses", 0))
    win_rate = float(stats.get("win_rate", 0) or 0)
    total_pnl = float(stats.get("total_pnl", 0) or 0)
    best = stats.get("best") or {}
    worst = stats.get("worst") or {}

    return f"""💵 수익 현황

[실전 테스트 기준]

총 거래 : {total}회
승 : {wins}회
패 : {losses}회
승률 : {win_rate:.2f}%

누적 손익 : ${total_pnl:,.4f}

최고 거래 : {best.get('symbol', '없음')} {float(best.get('pnl_pct', 0) or 0):+.4f}% / ${float(best.get('pnl', 0) or 0):,.4f}
최악 거래 : {worst.get('symbol', '없음')} {float(worst.get('pnl_pct', 0) or 0):+.4f}% / ${float(worst.get('pnl', 0) or 0):,.4f}

※ v4.3.2는 거래소 체결 평균가가 아니라 진입/청산 참고가 기준 추정치입니다.
다음 버전에서 BingX 체결내역 기반으로 더 정교화합니다."""


def live_profit_message(stats):
    # tuple 방어: 과거 콜백 버그로 stats가 tuple로 들어오면 마지막 dict만 사용
    if isinstance(stats, tuple):
        stats = stats[-1] if stats and isinstance(stats[-1], dict) else {}
    if stats is None:
        stats = {}
    best = stats.get("best") or {}
    worst = stats.get("worst") or {}

    best_text = "없음"
    if best:
        best_text = f"{best.get('symbol') or best.get('base')} {float(best.get('pnl_pct', 0) or 0):+.2f}% / {float(best.get('pnl', 0) or 0):+.4f} USDT"

    worst_text = "없음"
    if worst:
        worst_text = f"{worst.get('symbol') or worst.get('base')} {float(worst.get('pnl_pct', 0) or 0):+.2f}% / {float(worst.get('pnl', 0) or 0):+.4f} USDT"

    return f"""💵 내 수익 현황

• 총 누적 수익: {float(stats.get('total_pnl', 0) or 0):+.4f} USDT
• 승률: {float(stats.get('win_rate', 0) or 0):.1f}% ({int(stats.get('wins', 0))}승 / {int(stats.get('losses', 0))}패)
• 정산 완료: {int(stats.get('total', 0))}건 | 보유 중: {int(stats.get('holding', 0))}건

• 이번 달: {float(stats.get('month_pnl', 0) or 0):+.4f} USDT
• 이번 주: {float(stats.get('week_pnl', 0) or 0):+.4f} USDT

🏆 최고 거래: {best_text}
💔 최대 손실: {worst_text}"""

def live_entry_success_message(pos, order_result, signal=None):
    e = pos.get("entries", [{}])[-1]
    sig = signal or pos.get("signal") or {}
    return f"""🚀 실전 자동 진입 완료

거래소 : BingX Futures
전략 : Morning Short
종목 : {pos.get('base')}
심볼 : {pos.get('symbol')}
방향 : SHORT
레버리지 : 4배

진입 차수 : {e.get('level')}차
증거금 : ${float(e.get('margin', 0) or 0):,.4f}
주문가치 : ${float(e.get('order_value_usdt', 0) or 0):,.4f}
체결 평균가 : {e.get('price')}
체결 수량 : {e.get('qty')}

전략 조건:
✅ 15분봉 O→C +{float(sig.get('change_pct', 0) or 0):.2f}%
✅ 업비트+빗썸 교차상장
✅ BingX 선물 상장
✅ Top1 선정

TP : 레버리지 기준 +12%
SL : 16:00 이후 -30%
추가진입 : 불리하게 +3% 이동 시 2차/3차"""

def live_add_success_message(pos, order_result, level):
    e = pos.get("entries", [{}])[-1]
    return f"""⚠️ 실전 추가진입 완료

종목 : {pos.get('base')}
진입 차수 : {level}차
체결가 : {e.get('price')}
수량 : {e.get('qty')}
증거금 : ${float(e.get('margin', 0) or 0):,.4f}

현재 평균가 : {float(pos.get('avg_price', 0) or 0):.8f}
총 수량 : {float(pos.get('qty', 0) or 0):,.6f}"""

def live_close_success_message(pos):
    return f"""✅ 실전 포지션 청산 완료

종목 : {pos.get('base')}
심볼 : {pos.get('symbol')}

평균 진입가 : {float(pos.get('avg_price', 0) or 0):.8f}
청산가 : {pos.get('close_price')}
수익률 : {float(pos.get('pnl_pct', 0) or 0):+.2f}%
실현손익 : {float(pos.get('realized_pnl', 0) or 0):+.6f} USDT
수수료 : {float(pos.get('fee', 0) or 0):.6f} USDT
손익 출처 : {pos.get('realized_pnl_source')}

거래내역/수익현황에 반영했습니다."""

def live_entry_error_message(error):
    return f"""❌ 실전 자동 진입 실패

{error}

안전상 이번 신호는 진입하지 않았습니다.
Railway 로그와 BingX 포지션을 확인하세요."""

def live_skip_message(reason):
    return f"""⚠️ 실전 진입 스킵

사유:
{reason}

안전상 주문하지 않았습니다."""


def approval_status_text(status):
    mapping = {
        "PENDING": "🟡 승인 대기",
        "APPROVED": "✅ 승인 완료",
        "REJECTED": "❌ 승인 거절",
        "PAUSED": "⏸ 일시정지",
        "BLOCKED": "⛔ 차단",
        "PAPER_ONLY": "🧪 PAPER 전용",
    }
    return mapping.get(status, status or "미설정")

def admin_approval_request_message(state, balance=None):
    bal_text = f"{float(balance):,.2f} USDT" if balance is not None else "조회 전"
    return f"""👤 신규 승인 요청

chat_id : {state.get('user_chat_id')}
거래소 : BingX Futures
API : {'✅ 등록됨' if state.get('api_registered') else '❌ 미등록'}
API 테스트 : {'✅ 완료' if state.get('api_tested') else '⏳ 대기'}
시드 방식 : {'자동조회' if state.get('seed_mode') == 'auto' else '고정'}
사용 가능 잔고 : {bal_text}
승인 상태 : {approval_status_text(state.get('approval_status'))}

관리자만 승인/거절/보류할 수 있습니다."""

def user_approval_waiting_message():
    return """🟡 승인 대기

API 등록과 시드 설정이 완료되었습니다.
관리자 승인 후 트레이딩을 시작할 수 있습니다."""

def user_approved_message():
    return """✅ 승인되었습니다!

이제 ▶️ 트레이딩 시작을 눌러 자동매매를 시작하세요."""

def user_rejected_message():
    return """❌ 승인되지 않았습니다.

관리자에게 문의해주세요."""

def start_blocked_by_approval_message(status):
    return f"""⛔ 트레이딩 시작 불가

현재 승인 상태 : {approval_status_text(status)}

관리자 승인 후 트레이딩을 시작할 수 있습니다."""
