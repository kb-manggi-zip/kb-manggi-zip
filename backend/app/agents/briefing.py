"""브리핑 에이전트 — 비교표/화면 통역 문장 (LLM seam).

BriefingRequest{kind, context} → 문장. LLM 비활성 시 templates 폴백.
Phase B4: SSE 스트리밍 + verify(숫자 대조). 지금은 최종 문자열 반환.
"""
import logging

from ..core.llm import generate
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


def run(req: BriefingRequest) -> str:
    fallback = lambda: _fallback_for(req)  # noqa: E731
    return generate(
        system="주어진 비교/화면 facts를 사람이 읽기 쉽게 통역만 한다.",
        user=f"kind={req.kind}\nfacts={req.context}",
        fallback=fallback,
    )
