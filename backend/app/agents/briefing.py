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
    "비교표를 2~3문장의 짧은 대화체로 통역한다(채팅 말풍선에 들어갈 자연스러운 한 단락). "
    "제목·불릿·마크다운·항목 나열 금지. 월 부담이 가장 가벼운 갈래를 짚고, 매매는 상환액 일부가 "
    "자산으로 쌓인다는 점을 한 문장으로 덧붙이되 결론(무엇을 고르라)은 내리지 않는다. "
    "숫자는 facts에 있는 것만 인용하고, 없는 값은 언급하지 않는다."
)


def run(req: BriefingRequest) -> str:
    fallback = lambda: _fallback_for(req)  # noqa: E731
    return generate(
        system=_SYSTEM,
        user=f"kind={req.kind}\nfacts={req.context}",
        fallback=fallback,
    )


def stream(req: BriefingRequest) -> Iterator[str]:
    """SSE용 토큰 스트림. LLM 비활성 시 폴백 템플릿을 어절 단위로 흘린다."""
    fallback = lambda: _fallback_for(req)  # noqa: E731
    return llm_stream(
        system=_SYSTEM,
        user=f"kind={req.kind}\nfacts={req.context}",
        fallback=fallback,
    )
