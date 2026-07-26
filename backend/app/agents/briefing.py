"""브리핑 에이전트 — 비교표/화면 통역 문장 (LLM seam).

BriefingRequest{kind, context} → 문장. LLM 비활성 시 templates 폴백.
Phase B4: SSE 스트리밍 + verify(숫자 대조). 지금은 최종 문자열 반환.
"""

import logging
from collections.abc import Iterator
from functools import lru_cache

import yaml

from ..core.config import BACKEND_ROOT
from ..core.llm import generate
from ..core.llm import stream as llm_stream
from ..schemas import BriefingRequest, CompareResponse, Region
from . import templates

log = logging.getLogger("kb.agent.briefing")


@lru_cache
def _frames() -> dict:
    """에이전트 가이드 리소스(persona_frames.yaml) — 프롬프트를 코드에서 분리."""
    with open(BACKEND_ROOT / "app" / "agents" / "persona_frames.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _matches(cond: dict, contract: dict, finance: dict) -> bool:
    for key, want in cond.items():
        if key == "contract_type" and contract.get("type") != want:
            return False
        if key == "household" and finance.get("household") != want:
            return False
        if key == "under35" and bool(finance.get("under35")) != bool(want):
            return False
        if key == "first_home" and finance.get("firstHome") != want:
            return False
    return True


def build_system(ctx: dict) -> str:
    """사용자 상황에 매칭되는 frame(관점)들을 골라 base 페르소나 뒤에 주입."""
    cfg = _frames()
    contract = ctx.get("contract") or {}
    finance = ctx.get("finance") or {}
    hints = [fr["hint"] for fr in cfg["frames"] if _matches(fr["match"], contract, finance)]
    system = cfg["base"].strip()
    if hints:
        system += "\n\n[이 사용자에 해당하는 관점]\n- " + "\n- ".join(hints)
    return system


def _fallback_for(req: BriefingRequest) -> str:
    ctx = req.context or {}
    try:
        if req.kind == "compare":
            c = CompareResponse.model_validate(ctx["comparison"])
            return templates.compare(c, _honorific(ctx))
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


def _situation(ctx: dict) -> str:
    """contract·finance → 개인화 가이드용 상황 서술(한글). 라벨은 YAML에서."""
    c = ctx.get("contract") or {}
    f = ctx.get("finance") or {}
    labels = _frames().get("labels", {}).get("household", {})
    bits: list[str] = []
    if c.get("type"):
        bits.append(f"{c['type']} 계약")
    if f.get("household"):
        bits.append(labels.get(f["household"], f["household"]))
    if f.get("under35"):
        bits.append("만 35세 미만(청년 정책대출 대상 가능)")
    if f.get("firstHome") == "예":
        bits.append("생애최초 주택구입(LTV 우대 대상)")
    return ", ".join(bits) if bits else "상황 정보 제한"


def situation_of(ctx: dict) -> str:
    """상황 서술(공개) — graph intake_node 등에서 사용."""
    return _situation(ctx)


def _honorific(ctx: dict) -> str:
    """호칭 — 가구 라벨(persona_frames labels)에서 파생. 명시적 name이 오면 우선.

    (graph narrate_node가 호칭을 하드코딩하지 않도록 여기로 중앙화.)
    """
    if ctx.get("name"):
        return str(ctx["name"])
    f = ctx.get("finance") or {}
    labels = _frames().get("labels", {}).get("household", {})
    return labels.get(f.get("household"), "고객")


def _user_prompt(req: BriefingRequest) -> str:
    ctx = req.context or {}
    if req.kind == "compare":
        return (
            f"사용자 상황: {_situation(ctx)}\n"
            f"호칭: {_honorific(ctx)}\n"
            f"비교표(숫자는 여기 있는 값만 인용): {ctx.get('comparison')}"
        )
    return f"kind={req.kind}\nfacts={ctx}"


def run(req: BriefingRequest) -> str:
    if req.kind == "dayPlayer":
        # '이 동네에서의 하루' 개인화 내레이션 — narrator가 동네 실데이터+소비 프로필로 생성.
        # (context에 region/finance/branch가 오면 개인화, regionName만 오면 최소 폴백)
        from . import narrator

        return narrator.narrate_lifestyle(req.context or {})
    fallback = lambda: _fallback_for(req)  # noqa: E731
    return generate(system=build_system(req.context or {}), user=_user_prompt(req), fallback=fallback)


def stream(req: BriefingRequest) -> Iterator[str]:
    """SSE용 토큰 스트림. LLM 비활성 시 폴백 템플릿을 어절 단위로 흘린다."""
    if req.kind == "dayPlayer":
        from . import narrator

        system, user = narrator.build_lifestyle_prompt(req.context or {})
        return llm_stream(system=system, user=user, fallback=lambda: narrator.lifestyle_fallback(req.context or {}))
    fallback = lambda: _fallback_for(req)  # noqa: E731
    return llm_stream(system=build_system(req.context or {}), user=_user_prompt(req), fallback=fallback)
