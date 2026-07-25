"""브리핑 에이전트 — 비교표/화면 통역 문장 (LLM seam).

BriefingRequest{kind, context} → 문장. LLM 비활성 시 templates 폴백.
Phase B4: SSE 스트리밍 + verify(숫자 대조). 지금은 최종 문자열 반환.
"""

import logging
from collections.abc import Iterator

from ..core.llm import generate
from ..core.llm import stream as llm_stream
from ..schemas import BriefingRequest, CompareResponse, Region
from . import templates

log = logging.getLogger("kb.agent.briefing")


def _fallback_for(req: BriefingRequest) -> str:
    ctx = req.context or {}
    try:
        if req.kind == "compare":
            c = CompareResponse.model_validate(ctx["comparison"])
            return templates.compare(c, str(ctx.get("name", "고객")))
        if req.kind == "regions":
            return templates.regions(Region.model_validate(ctx["region"]))
        if req.kind == "renewal":
            return templates.renewal(str(ctx.get("noticeDate", "[기한]")))
        if req.kind == "revisit":
            return templates.revisit(int(ctx.get("daysCloser", 0)))
        if req.kind == "dayPlayer":
            return templates.day_player(str(ctx.get("regionName", "선택 동네")))
        if req.kind == "savedMoney":
            return templates.saved_money()
        if req.kind == "finance":
            return templates.finance(str(ctx.get("branch", "")), str(ctx.get("reason", "")))
    except Exception as e:  # context 불완전 → 조용히 삼키지 않고 로깅 후 안전 문구
        log.warning("briefing 폴백 컨텍스트 파싱 실패(kind=%s): %s", req.kind, e)
    return "계산 결과를 정리했어요."


_SYSTEM = (
    "너는 이 사용자의 '상황'에 맞춰 비교표를 통역·가이드하는 주거금융 도우미다. "
    "2~3문장의 짧은 대화체(채팅 말풍선, 마크다운·불릿·제목 금지). "
    "사용자 상황에 따라 관점을 고른다: 월세면 '매달 사라지는 돈' 관점, 신혼·자녀면 자산형성·주거안정, "
    "만35세 미만이면 청년 정책대출(버팀목·디딤돌) 여지, 생애최초면 LTV 우대 가능성. "
    "월 부담이 가장 가벼운 갈래를 짚고, 매매는 상환액 일부가 자산으로 쌓인다는 점을 덧붙이되 "
    "결론(무엇을 고르라)·권유는 하지 않는다. 숫자는 facts에 있는 것만 인용하고 없는 값은 언급하지 않는다."
)

_HOUSEHOLD = {"1인": "1인 가구", "신혼": "신혼 가구", "자녀": "자녀 있는 가구"}


def _situation(ctx: dict) -> str:
    """contract·finance → 개인화 가이드용 상황 서술(한글)."""
    c = ctx.get("contract") or {}
    f = ctx.get("finance") or {}
    bits: list[str] = []
    if c.get("type"):
        bits.append(f"{c['type']} 계약")
    if f.get("household"):
        bits.append(_HOUSEHOLD.get(f["household"], f["household"]))
    if f.get("under35"):
        bits.append("만 35세 미만(청년 정책대출 대상 가능)")
    if f.get("firstHome") == "예":
        bits.append("생애최초 주택구입(LTV 우대 대상)")
    return ", ".join(bits) if bits else "상황 정보 제한"


def _user_prompt(req: BriefingRequest) -> str:
    ctx = req.context or {}
    if req.kind == "compare":
        return (
            f"사용자 상황: {_situation(ctx)}\n"
            f"호칭: {ctx.get('name', '고객')}\n"
            f"비교표(숫자는 여기 있는 값만 인용): {ctx.get('comparison')}"
        )
    return f"kind={req.kind}\nfacts={ctx}"


def run(req: BriefingRequest) -> str:
    fallback = lambda: _fallback_for(req)  # noqa: E731
    return generate(system=_SYSTEM, user=_user_prompt(req), fallback=fallback)


def stream(req: BriefingRequest) -> Iterator[str]:
    """SSE용 토큰 스트림. LLM 비활성 시 폴백 템플릿을 어절 단위로 흘린다."""
    fallback = lambda: _fallback_for(req)  # noqa: E731
    return llm_stream(system=_SYSTEM, user=_user_prompt(req), fallback=fallback)
