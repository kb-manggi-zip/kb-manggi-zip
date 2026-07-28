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


def build_persona(
    contract: dict,
    finance: dict,
    budget: int = 0,
    clarify_result: Optional[dict] = None,
    persona_id: Optional[str] = None,
) -> dict:
    """페르소나 → PersonaProfile(dict). 화면 개인화 카드 = 이 산출물.

    소비 성향 증거 위계: 3위 세그먼트 통계 → 2위 개인 실측(persona_id) → 1위 본인 진술(clarify).
    강한 증거가 약한 증거를 덮어쓰며, consumptionSignals에 각 값의 출처를 태그한다.
    """
    household = finance.get("household") or "1인"
    note = contract.get("note") or ""

    prof = profile_for(household)
    workplace = (prof.get("workplace") or {}).get("name")
    consumption = list(prof.get("traits", []))

    # ── 소비 성향 신호(출처 태그) — 세그먼트 → 실측 override → 진술 순 ──
    signals = [{"label": t, "source": "세그먼트"} for t in consumption]
    if persona_id:
        from .personal_traits import derive_personal_traits

        for cat, o in derive_personal_traits(persona_id).items():
            lvl = "많이 쓰는 편" if o["level"] == "high" else "적게 쓰는 편"
            signals.append(
                {"label": f"{cat} {lvl}", "source": "실측", "reason": f"{o['reason']} · 시연용 합성 데이터 기준"}
            )
    for s in (clarify_result or {}).get("noteSignals", []):
        signals.append({"label": s, "source": "진술"})

    base_weights = clarify_mod.note_weights(household, "")  # 가구 기본(자유입력 보정 전)
    weights = clarify_mod.note_weights(household, note, contract.get("noteAdjust"))
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
        "baseWeights": base_weights,  # 가구 기본 가중치(before). weights=반영 후(after) → 화면 대비 표시(B4)
        "weightBasis": WEIGHT_BASIS,
        "consumption": consumption,
        "consumptionSignals": signals,
        "resources": _resources(workplace, consumption),
        "budgetBand": _budget_band(budget),
    }


def scoring_ctx(
    contract: dict, finance: dict, budget: int, in_preferred: Optional[bool], persona_id: Optional[str] = None
) -> dict:
    """페르소나 → 동네 스코어 입력(단일 소스). regions 노드가 인라인으로 만들던 ctx를 여기로 통일.

    자유입력 보정 가중치(weights) + values_food(성향 판정) 둘 다 여기서 확정한다.
    values_food 증거 위계(personal_traits.py 문서 그대로): 1위 본인 진술(자유입력) > 2위 개인
    실측(mydata) > 3위 세그먼트 평균(scoring.py 폴백, 여기서 값을 안 주면 그쪽에서 traits로 추정).
    가중치(weights)만 자유입력을 반영하고 판정(values_food)은 세그먼트 평균에 고정돼있던
    불일치를 없애기 위해, 본인 진술을 실측보다 나중에(=더 높은 우선순위로) 적용한다.
    """
    household = finance.get("household")
    note = contract.get("note") or ""
    prof = profile_for(household)
    ctx = {
        "household": household,
        "budget": budget,
        "workplace": (prof.get("workplace") or {}).get("name"),
        "traits": prof.get("traits", []),
        "in_preferred": in_preferred,
        # 확정된 조정(noteAdjust)이 있으면 그걸로 랭킹(자연어→LLM 확정분 반영), 없으면 note 키워드.
        "weights": clarify_mod.note_weights(household, note, contract.get("noteAdjust")),
    }
    if persona_id:
        from .personal_traits import derive_personal_traits, values_food_override

        vf = values_food_override(derive_personal_traits(persona_id))
        if vf is not None:
            ctx["values_food"] = vf  # 2위: 실측이 세그먼트 성향을 덮어씀
    vf_note = clarify_mod.note_values_food(note)
    if vf_note is not None:
        ctx["values_food"] = vf_note  # 1위: 본인 진술이 실측·세그먼트를 덮어씀
    return ctx
