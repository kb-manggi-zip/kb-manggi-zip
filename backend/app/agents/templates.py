"""폴백 템플릿 — 프론트 src/data/briefings.ts 이식.

LLM 비활성/부적합 시 이 결정론적 문장을 반환한다.
⚠️ 문장 규칙: "추천합니다/하세요/이득" 금지, 서술만.
"""

from ..schemas import CompareResponse, Region
from ..tools.format import format_amount

_BRANCH_KOR = {"갱신": "눌러앉기", "이사": "옮기기", "매매": "사기"}


def _lightest(c: CompareResponse) -> str:
    first = sorted(c.branches, key=lambda b: b.monthlyBurden)[0]
    return _BRANCH_KOR.get(first.branch, first.branch)


def _buy_monthly(c: CompareResponse) -> str:
    b = next((br for br in c.branches if br.branch == "매매"), None)
    return format_amount(b.monthlyBurden) if b else "-"


def compare(c: CompareResponse, name: str) -> str:
    return (
        f"{name}님, 세 경우를 계산했어요. 매달 부담만 보면 {_lightest(c)}가 가장 가볍지만, "
        f"사기의 월 {_buy_monthly(c)} 중 일부는 이자가 아니라 자산으로 쌓여요. "
        f"어느 쪽이 맞는지는 {name}님의 계획에 달려 있어요."
    )


def regions(top: Region) -> str:
    return (
        "예산 안에서 최근 거래가 활발한 순서로 골랐어요. "
        f"{top.name}은 예산 대비 {format_amount(top.surplus)} 여유가 있어요."
    )


def renewal(notice_date: str) -> str:
    return f"눌러앉기를 고르셨네요. 통보 기한({notice_date})까지 챙길 것 네 가지를 정리했어요."


def revisit(days_closer: int) -> str:
    return f"지난번 계산 이후 만기가 {days_closer}일 더 가까워졌어요."


def day_player(region_name: str) -> str:
    return f"{region_name}에서의 하루를 만들었어요."


def saved_money() -> str:
    return "눌러앉으면 아끼는 돈의 쓰임을 정리했어요."


def finance(branch: str, reason: str) -> str:
    return f"{branch} 경로에 맞는 상품을 골랐어요. {reason}"
