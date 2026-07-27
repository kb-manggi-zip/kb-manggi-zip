"""개인화 '조합' 레이어 — 완성된 페르소나에 맞춰 리소스를 한 번에 조합.

이 파일이 생기기 전까지 개인화 리소스는 흩어져 각자 쓰였다:
  - scoring.weights_for()  → 동네 순위 가중치
  - narrator.profile_for() → 발품 소비 프로필·직장
  - clarify.note_*()       → 자유입력 반영
'완성된 페르소나 → 리소스 조합 → 산출물'이라는 명시적 단계가 없었다.

여기서 그 조합을 한 곳에 모은다:
  1) build_persona(): 페르소나 → PersonaProfile(화면 '개인화 프로필 카드' 산출물)
  2) scoring_ctx():   페르소나 → 동네 스코어 입력(regions 노드가 이걸 씀 = 단일 소스)

숫자·근거는 전부 결정론(순수). LLM은 이 조합을 '서술'하는 narrator에서만.
"""

from typing import Optional

from ..agents import clarify as clarify_mod
from ..agents.narrator import profile_for

WEIGHT_BASIS = "국토부 2024 주거실태조사 이사사유 응답률 + 가구 세그먼트 조정 (자유입력 시 보정·재정규화)"


def _budget_band(budget: int) -> str:
    if not budget or budget <= 0:
        return "예산 정보 없음 (월세 등 — 거래 활발 동네 기준)"
    return f"약 {budget / 1e8:.1f}억 이내 후보에서 선별 (예산 초과 동네는 0단계 하드필터로 제외)"


def _resources(workplace: Optional[str], consumption: list[str]) -> list[str]:
    """이 페르소나의 발품에 실제 등장할 리소스만 조합('빼기의 개인화')."""
    out = []
    if workplace:
        out.append(f"통근 실측 기준 직장: {workplace} (ODsay)")
    out.append("반경 상권 집계 (소상공인 상권 API)")
    out.append("국토부 실거래 사례")
    if consumption:
        out.append("연령 세그먼트 소비 성향 (카드소비 통계)")
    return out


def build_persona(contract: dict, finance: dict, budget: int = 0, clarify_result: Optional[dict] = None) -> dict:
    """페르소나 → PersonaProfile(dict). 화면 개인화 카드 = 이 산출물.

    clarify_result가 있으면 그 우선순위/신호를 반영(닫힌 루프의 '확정' 결과).
    없으면 폼값만으로 조합.
    """
    household = finance.get("household") or "1인"
    note = contract.get("note") or ""

    prof = profile_for(household)
    workplace = (prof.get("workplace") or {}).get("name")
    consumption = prof.get("traits", [])

    weights = clarify_mod.note_weights(household, note)
    priorities = (clarify_result or {}).get("priorities") or [
        clarify_mod.AXIS_LABEL[k] for k, _ in sorted(weights.items(), key=lambda kv: -kv[1])
    ]
    segment = clarify_mod.segment_label(household)
    top = priorities[0] if priorities else "생활 균형"

    return {
        "segment": segment,
        "headline": f"{segment} · '{top}'을 가장 중시",
        "workplace": workplace,
        "weights": weights,
        "weightBasis": WEIGHT_BASIS,
        "consumption": consumption,
        "resources": _resources(workplace, consumption),
        "budgetBand": _budget_band(budget),
    }


def scoring_ctx(contract: dict, finance: dict, budget: int, in_preferred: Optional[bool]) -> dict:
    """페르소나 → 동네 스코어 입력(단일 소스). regions 노드가 인라인으로 만들던 ctx를 여기로 통일.

    자유입력 보정 가중치(weights)를 함께 실어 명확화가 순위에 반영되게 한다.
    """
    household = finance.get("household")
    note = contract.get("note") or ""
    prof = profile_for(household)
    return {
        "household": household,
        "budget": budget,
        "workplace": (prof.get("workplace") or {}).get("name"),
        "traits": prof.get("traits", []),
        "in_preferred": in_preferred,
        "weights": clarify_mod.note_weights(household, note),
    }
