"""개인화 동네 스코어 — 통계 근거 가중합 (블랙박스 ML 아님, 임의 가중치 금지).

핵심: 가중치조차 **국토부 2024 주거실태조사 이사사유 응답률**에서 도출한다("감으로 0.35" 금지).
계산은 순수·투명(설명가능), narrator/화면이 근거를 그대로 노출한다.

축(4): commute(통근) · budget(예산적합) · consumption(소비매치) · preference(선호지역)
데이터: 통근=region_transit(ODsay 실측) · 소비=region_facts(상권) · 예산=surplus · 선호=구 매칭.
"""

from typing import Optional

from . import trades_store

# 시군구코드 → 수집된 구 fact-id(상권·통근 자료가 있는 대표 id). 동 facts 없을 때 '구 기준' 폴백.
_FACT_ID_BY_SIGUNGU = {
    "11260": "jungnang",
    "11290": "seongbuk",
    "11320": "dobong",
    "11350": "nowon",
    "11380": "eunpyeong",
    "11440": "mapo",
}

# ── 가중치 도출: 국토부 2024 주거실태조사 '이사 이유' 응답률 (원문 <표 10> 확정) ──────────
# 출처: 2024년도 주거실태조사 통계보고서 <표 10> '현재 주택으로 이사한 이유'(전국·복수응답 %).
# 4축 모두 원문 항목값에서 도출(감/근사 아님). 항목명과 값:
#   commute     = 직주근접·직장 변동 때문에                                        30.6
#   consumption = 교통이 편리하고, 편의·문화시설·공원·녹지 등이 좋은 지역           25.5
#   preference  = 부모·자녀 등과 가까이(8.1) + 자녀 양육·교육환경(3.0)              11.1
#   budget      = 집값 혹은 집세가 너무 비싸고 부담스러워서                          8.3
# ※ 정직성 기록: 과거 코드/문서는 25.5를 '교통편리'로 보고 통근에 합산(56.1)했으나, 원문 항목명은
#   교통·편의·문화·녹지가 묶인 '복합 생활환경' 항목이라 통근 전용이 아님 → consumption으로 재매핑(수정).
# 배제: 시설·설비 양호(47.2)·규모 적합(20.3)=주택 내부속성(미채점) / 계약만기·통보·재개발=비자발적 이사
#       / 결혼·독립·내집마련·귀농=생애이벤트·PoC 범위 밖 → 어느 축에도 매핑 안 함.
SURVEY_RATIOS = {
    "commute": 0.306,  # 직주근접·직장 변동
    "consumption": 0.255,  # 교통 편리·편의문화시설·공원녹지 (복합 생활환경)
    "budget": 0.083,  # 집값·집세 부담
    "preference": 0.111,  # 부모·자녀 근접 8.1 + 자녀 양육·교육환경 3.0
}

# 페르소나 세그먼트 조정 (근거 있는 배수 — 임의 아님)
#  청년(1인): 청년의삶 실태조사 통근 39.2% 1위 → commute↑
#  신혼: 주거실태조사 신혼 '주택구입·정주 지향' → budget·preference↑
PERSONA_ADJUST = {
    "1인": {"commute": 1.3},
    "신혼": {"budget": 1.3, "preference": 1.2},
    "자녀": {"preference": 1.3, "consumption": 1.2},  # 학군·생활 인프라 중시
}


def derive_weights(ratios: Optional[dict] = None) -> dict:
    """응답률 → 정규화 가중치(합=1). 하드코딩이 아니라 통계에서 '계산'됨을 증명."""
    r = ratios or SURVEY_RATIOS
    total = sum(r.values())
    return {k: round(v / total, 3) for k, v in r.items()}


def weights_for(household: Optional[str]) -> dict:
    """가구 세그먼트 조정 후 재정규화한 가중치."""
    w = derive_weights()
    adj = PERSONA_ADJUST.get(household or "", {})
    w = {k: v * adj.get(k, 1.0) for k, v in w.items()}
    total = sum(w.values())
    return {k: round(v / total, 3) for k, v in w.items()}


# ── 축별 점수(0~1, 순수) — 각 함수에 근거 주석 ──────────────────────────────
def score_commute(minutes: Optional[int]) -> float:
    """통근 30분 이하 만점, 60분 0점(통근시간-만족도 통용 분기). 데이터 없으면 중립 0.5."""
    if minutes is None:
        return 0.5
    return max(0.0, min(1.0, (60 - minutes) / 30))


def _bell(x: float, peak: float, width: float) -> float:
    return max(0.0, 1 - ((x - peak) / width) ** 2)


def score_budget(price: int, budget: int) -> float:
    """예산 대비 여유 10%에서 최대(적정가). 너무 싸거나(여유 과다) 빠듯하면 감점."""
    if budget <= 0 or price <= 0:
        return 0.5
    return _bell((budget - price) / budget, peak=0.10, width=0.20)


def score_consumption(dining_cafe_count: Optional[int], values_food: bool) -> float:
    """동네 외식·카페 밀집도(상권 실측) × 소비 성향. 성향이 아니면 밀집 가중을 낮춤."""
    if not dining_cafe_count:
        return 0.5
    density = min(dining_cafe_count / 200, 1.0)  # 200곳↑ 만점
    return density if values_food else 0.4 + 0.3 * density


def score_preference(in_preferred: Optional[bool]) -> float:
    """선호지역 지정 시 그 구면 만점(필터로 이미 맞춤), 미지정이면 중립."""
    if in_preferred is None:
        return 0.6
    return 1.0 if in_preferred else 0.3


# ── 종합 스코어 + 근거 ────────────────────────────────────────────────────
def _dc_count(region_id: str) -> Optional[int]:
    vals = trades_store.read_region_facts(region_id).get("dining_cafe") or []
    # "음식점·카페 316곳 밀집" → 316
    import re

    m = re.search(r"(\d+)", vals[0]) if vals else None
    return int(m.group(1)) if m else None


def score_region(region: dict, ctx: dict) -> dict:
    """region(dict) + ctx(household·budget·workplace·in_preferred) → {total, reasons, breakdown}.

    통근/소비는 DB(실측·상권)에서 조회. 가중치는 weights_for(가구).
    """
    household = ctx.get("household")
    budget = ctx.get("budget") or 0
    # ctx에 보정 가중치(persona.scoring_ctx가 자유입력 반영해 실어줌)가 있으면 그걸, 없으면 가구 기본.
    w = ctx.get("weights") or weights_for(household)
    rid = region.get("id") or ""

    # 동 facts 없으면 같은 구(fact-id)로 폴백 — '구 기준'으로 표기(동 특성처럼 단정 금지).
    gu_id = _FACT_ID_BY_SIGUNGU.get(region.get("sigunguCode") or "")
    gu_used = False

    # commute: region_transit 캐시(실측) 조회 (동 → 구 폴백)
    wp = ctx.get("workplace")
    tr = (trades_store.read_region_transit(rid, wp) if wp else None) or None
    if tr is None and wp and gu_id:
        tr = trades_store.read_region_transit(gu_id, wp)
        if tr:
            gu_used = True
    minutes = tr["minutes"] if tr else None

    dc = _dc_count(rid)
    if dc is None and gu_id:
        dc = _dc_count(gu_id)
        if dc:
            gu_used = True
    # 실측 override(persona.scoring_ctx가 실어줌)가 있으면 그것을, 없으면 세그먼트 traits에서 판정.
    values_food = ctx.get("values_food")
    if values_food is None:
        values_food = any(k in " ".join(ctx.get("traits") or []) for k in ("카페", "외식", "배달"))

    axes = {
        "commute": score_commute(minutes),
        "budget": score_budget(region.get("midPrice", 0), budget),
        "consumption": score_consumption(dc, values_food),
        "preference": score_preference(ctx.get("in_preferred")),
    }
    total = round(sum(axes[k] * w[k] for k in axes), 3)

    gu_tag = " (구 기준)" if gu_used else ""
    reasons = []
    if minutes is not None:
        # 직장은 문진 입력이 아니라 '가구 세그먼트 대표 직장 가정' → 통근값 옆에 명시(아는 척 금지).
        cw = int(w["commute"] * 100)
        reasons.append(f"통근 {minutes}분{gu_tag} (가중치 {cw}%·조사상 최우선·세그먼트 대표 직장 기준)")
    if dc:
        # 적합도 프레임: '취향 추론'이 아니라 '자주 쓰는 곳이 가까워 생활 마찰이 적다'(G4).
        near_note = " — 자주 쓰는 곳이 가까운 동네" if values_food else ""
        reasons.append(f"음식점·카페 {dc}곳{gu_tag}{near_note}")
    if budget > 0 and region.get("surplus", 0) > 0:
        reasons.append("예산 여유 있음")
    return {"total": total, "reasons": reasons, "breakdown": {k: round(axes[k], 3) for k in axes}, "weights": w}


def rank(regions: list[dict], ctx: dict, top: int = 3) -> list[dict]:
    """후보를 개인화 스코어로 재정렬 → 상위 top. 각 region에 score·scoreReasons 부착."""
    scored = []
    for r in regions:
        s = score_region(r, ctx)
        r = {**r, "score": s["total"], "scoreReasons": s["reasons"]}
        scored.append(r)
    scored.sort(key=lambda r: r["score"], reverse=True)
    return scored[:top]
