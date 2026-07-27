"""슈퍼바이저 라우터 — '어떤 규칙 세트를 쓸지 / 어떤 갈래가 현실적인지'를 고르는 **결정론 라우팅**.

⚠️ 정직한 표기: 이 노드는 **if문 기반 결정론**이다. 자율 에이전트가 아니다.
   "에이전트"라는 말은 이 노드들을 잇는 **LangGraph 오케스트레이션**(노드 분리·추적·독립수정)을 가리키지,
   이 함수가 스스로 판단한다는 뜻이 아니다. 여기서 LLM은 호출하지 않는다.

핵심 원칙: **계산은 규칙(결정론). 여기선 '적용 선택'만.**
경우의 수(주택유형 × 상황)가 늘수록, 여기저기 흩어진 if문 대신 이 라우터 한 곳으로 모으는 게 유지보수 우위.

두 축:
  1) 규칙 세트 라우팅(주택유형) — RULE_PROFILES. 현재 '주택'만 구현, '오피스텔'(준주택)은 seam.
  2) 갈래 현실성 라우팅 — 상황 → 갈래별 현실성 코멘트(결정론). narrate가 반영해 개인화 통역.
라우팅 자체는 결정론(안전). 그 결과를 '개인화 통역'하는 것만 LLM(narrate). 숫자는 절대 안 건드림.
"""

# ── 주택유형별 규칙 세트 프로필 (확장 seam) ──────────────────────────────
# compare/policy_loans/rules는 현재 '주택'(아파트·연립다세대) 기준으로 계산한다.
# 새 유형(오피스텔=준주택 등)은 세율·대출·규제가 통째로 달라 별도 rule set 필요 → 사람 리서치.
RULE_PROFILES = {
    "주택": {  # 아파트·연립다세대 — 현재 compare가 쓰는 규칙 세트
        "supported": True,
        "acquisition": "지방세법 §11-8 주택특례(1~3%) + 생애최초 감면",
        "loans": "디딤돌·버팀목(주택 대상) · 규제지역 LTV",
    },
    "오피스텔": {  # 준주택 — ⚠️ 별도 규칙 세트 필요(사람 리서치, docs/에이전트_로드맵.md)
        "supported": False,
        "todo": "취득세 일반세율(§11-7 ~4%대)·생애최초 감면 제외 여부·준주택 담보대출·주택수 산정 특례",
    },
}


def select_profile(housing_type: str) -> dict:
    """주택유형 → 규칙 세트 프로필. 미지원 유형은 주택으로 폴백(+supported=False 신호)."""
    return RULE_PROFILES.get(housing_type, RULE_PROFILES["주택"])


def _branch_notes(contract: dict, finance: dict) -> dict:
    """갈래별 현실성/유불리 코멘트(결정론) — 규칙 로직과 일관되게."""
    notes: dict = {}
    if contract.get("renewalUsed") == "사용":
        notes["갱신"] = "법정 갱신권을 이미 사용해 갱신 거절 협의가 필요할 수 있음"
    if finance.get("under35"):
        notes["이사"] = "만 35세 미만 → 청년 버팀목 전세대출 우대 여지"
    if finance.get("firstHome") == "예":
        notes["매매"] = "생애최초 → LTV 우대(70%)로 매매 문턱이 상대적으로 낮음"
    return notes


def _budget_reference_branch(finance: dict, available: list) -> str | None:
    """persona budgetBand '표기용' 참조 갈래(권유 아님, trace/서술용).

    저널리(analyze) 그래프엔 아직 사용자가 고른 갈래가 없어 예산 밴드 기준 갈래가 필요하다.
    상황상 '여지가 가장 큰' 갈래를 결정론으로 고른다(실제 UI 카드는 프론트가 고른 갈래 예산을 직접 전달).
    """
    if finance.get("firstHome") == "예" and "매매" in available:
        return "매매"
    if "이사" in available:
        return "이사"
    return available[0] if available else None


def route(contract: dict, finance: dict, comparison: dict, housing_type: str = "주택") -> dict:
    """규칙 세트 선택 + 갈래 현실성 라우팅.

    ⚠️ 결정론 라우팅이다(에이전트/자율 아님) — 규칙은 사람이 인코딩, 여기선 if로 '적용 선택'만.
    housing_type: 향후 입력 필드(ContractInfo 확장 시). 현재는 '주택' 고정(스키마 변경 전).
    반환: narrate가 참고할 라우팅 결정(숫자 없음, 결정론).
    """
    profile = select_profile(housing_type)
    available = [b.get("branch") for b in comparison.get("branches", [])]
    return {
        "profile": housing_type,
        "profile_supported": profile["supported"],
        "branch_notes": _branch_notes(contract, finance),
        "available_branches": available,
        "branch": _budget_reference_branch(finance, available),  # budgetBand 참조용(권유 아님)
    }
