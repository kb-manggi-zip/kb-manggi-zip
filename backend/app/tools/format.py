"""숫자 포맷 — 프론트 engine/compare.ts 의 로컬 formatAmt 와 1:1.

⚠️ 헤드라인·cares 문자열이 이 포맷 결과를 그대로 담으므로,
   프론트 동치를 위해 JS Math.round 반올림(half-up)을 정확히 재현한다.
   (Python 기본 round는 banker's rounding이라 사용하지 않는다.)
"""
import math


def js_round(x: float) -> int:
    """JS Math.round 재현: 0.5는 +∞ 방향으로."""
    return math.floor(x + 0.5)


def format_amt(won: int) -> str:
    """compare.ts 의 로컬 formatAmt 이식 (헤드라인/cares에서 사용)."""
    if won >= 100_000_000:
        eok = math.floor(won / 100_000_000)
        man = js_round((won % 100_000_000) / 10_000)
        return f"{eok}억 {man:,}만" if man > 0 else f"{eok}억"
    return f"{js_round(won / 10_000):,}만"


def format_amount(won: int) -> str:
    """utils/format.ts 의 범용 formatAmount 이식 (briefings 템플릿에서 사용).

    format_amt 와 미세하게 다르다(억 단위 표기·원 단위 처리). 프론트 계약 유지 위해 분리.
    """
    if won >= 100_000_000:
        eok = won / 100_000_000
        man = js_round((won % 100_000_000) / 10_000)
        if man == 0:
            return f"{js_round(eok)}억"
        return f"{math.floor(eok)}억 {man:,}만"
    if won >= 10_000:
        return f"{js_round(won / 10_000):,}만"
    return f"{won:,}원"
