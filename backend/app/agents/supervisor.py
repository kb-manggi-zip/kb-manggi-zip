"""슈퍼바이저 라우터 — 상황을 읽고 '어떤 규칙을 어떻게 적용할지' 판단(라우팅).

핵심 원칙: **계산은 규칙(결정론). "어떤 규칙 세트를 쓸지 / 어떤 갈래가 현실적인지" 선택만 여기서.**
경우의 수(주택유형 × 상황)가 늘수록, 하드코딩 if문 대신 이 라우터가 유지보수·확장 우위.
→ 이것이 "왜 에이전트인가"의 실체: 규칙은 사람이 인코딩, **적용 라우팅은 에이전트**.

두 축:
  1) 규칙 세트 라우팅(주택유형) — RULE_PROFILES. 현재 '주택'만 구현, '오피스텔'(준주택)은 seam.
  2) 갈래 현실성 라우팅 — 상황 → 갈래별 현실성 코멘트(결정론). narrate가 반영해 개인화 통역.
라우팅 자체는 결정론(안전). 그 판단을 '개인화 통역'하는 것만 LLM(narrate). 숫자는 절대 안 건드림.
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


def route(contract: dict, finance: dict, comparison: dict, housing_type: str = "주택") -> dict:
    """규칙 세트 선택 + 갈래 현실성 라우팅.

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
    }
