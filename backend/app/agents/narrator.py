"""내레이터 에이전트 — 갈래×동네 → 하루 씬 + '이 동네에서의 하루' 개인화 내레이션.

1) run(): 씬 카드(구조)는 agents/scenes.yaml에서 로드(코드-데이터 분리).
   - regionId가 scenes.yaml `regions`에 있으면 지역별 씬 우선, 없으면 branch base.
   - '월세로'(regionId '…-m')와 '전세로'가 서로 다른 하루로 나온다.
   - 숫자(monthlyCost)는 YAML 값(계산 아님).

2) narrate_lifestyle(): 동네 실데이터(이름·태그) + 소비 프로필(spending_profiles.yaml) →
   생성형 '온라인 발품' 내레이션(LLM). llm_active 아니면 결정론 폴백.
   - ⚠️ 금액은 여기서 만들지 않는다(정성적 서술만). 금융 숫자는 compare가 담당.
   - 소비 프로필은 PoC 가정 → 실서비스는 KB 카드데이터로 파일만 교체(같은 shape).
"""

from functools import lru_cache
from pathlib import Path

import yaml

from ..core.config import BACKEND_ROOT
from ..core.llm import generate
from ..schemas import Branch, Scene, SimulateResponse
from ..tools import molit, trades_store, transit

_SCENES_YAML = Path(__file__).parent / "scenes.yaml"
_PROFILES_YAML = Path(__file__).parent / "spending_profiles.yaml"
_REGION_FACTS_YAML = BACKEND_ROOT / "data" / "region_facts.yaml"


@lru_cache(maxsize=1)
def _registry() -> dict:
    with _SCENES_YAML.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


# ── 하루시뮬 동적 씬 (docs/하루시뮬_이미지생성_계획.md 확정 구조) ──────────────
# 고정 3씬: 초역세권 있으면 통근+상권태그2, 없으면 상권태그3. 태그 우선순위는 소비신호로.
_TAG_ALIASES = {"카페거리": "음식점·카페 밀집", "한강공원": "공원 인접"}  # 소수 수기 태그 정규화
_TAG_FALLBACK_ORDER = ["음식점·카페 밀집", "공원 인접", "마트·편의점 밀집", "여가시설 밀집", "학원가"]
_SIGNAL_TAG_MATCH = [  # 문서 §씬 배치 매칭표 그대로 (배달은 매칭 없음 → 폴백)
    (("카페", "식비"), "음식점·카페 밀집"),
    (("여가",), "여가시설 밀집"),
    (("쇼핑",), "마트·편의점 밀집"),
]
_TAG_SCENE_META = {
    "음식점·카페 밀집": {"emoji": "☕", "caption1": "음식점·카페 골목이 가까운 동네"},
    "공원 인접": {"emoji": "🌳", "caption1": "공원이 가까운 동네"},
    "마트·편의점 밀집": {"emoji": "🛒", "caption1": "마트·편의점이 가까운 생활권"},
    "여가시설 밀집": {"emoji": "🎳", "caption1": "여가시설이 가까운 동네"},
    "학원가": {"emoji": "📚", "caption1": "학원가가 가까운 동네"},
}
_TIMES_WITH_COMMUTE = ["🌅 07:40", "☀️ 12:30", "🌇 18:30"]
_TIMES_NO_COMMUTE = ["🌅 09:00", "☀️ 12:30", "🌇 18:30"]

# 씬 이미지(docs/하루시뮬_이미지생성_계획.md) — 태그→파일 slug. scripts/generate_scene_images.py가
# 이 매핑을 그대로 가져다 써서 파일명 규칙이 어긋나지 않게 한다(단일 소스).
_TAG_SLUG = {
    "음식점·카페 밀집": "cafe",
    "공원 인접": "park",
    "마트·편의점 밀집": "mart",
    "여가시설 밀집": "leisure",
    "학원가": "academy",
}
_COMMUTE_SLUG = "commute"
SCENE_IMAGE_DIR = BACKEND_ROOT / "data" / "scene_images"


def _scene_image_url(region_id: str, slug: str) -> str:
    """생성된 이미지가 실제로 있을 때만 URL 반환 — 없으면 ''(프론트가 시간대 그라디언트로 폴백, 에러 아님)."""
    path = SCENE_IMAGE_DIR / f"{region_id}_{slug}.png"
    if not path.exists():
        return ""
    from urllib.parse import quote

    return f"/static/scene_images/{quote(path.name)}"


def _lead_signal_tag(lead_signal: str | None) -> str | None:
    """'카페 소비 많이 하는 편' 같은 라벨 → 우선 태그. 매칭 규칙 없으면(배달 등) None(폴백행)."""
    if not lead_signal:
        return None
    for keywords, tag in _SIGNAL_TAG_MATCH:
        if any(k in lead_signal for k in keywords):
            return tag
    return None


def _pick_content_tags(raw_tags: list[str], lead_signal: str | None, count: int) -> list[str]:
    """그 동이 실제로 가진 상권 태그 중 count개 — 소비신호 매칭 태그 우선, 나머진 고정 폴백 순서."""
    tags = {_TAG_ALIASES.get(t, t) for t in raw_tags}
    matched = _lead_signal_tag(lead_signal)
    ordered: list[str] = []
    if matched and matched in tags:
        ordered.append(matched)
    for tag in _TAG_FALLBACK_ORDER:
        if tag in tags and tag not in ordered:
            ordered.append(tag)
    return ordered[:count]


def _commute_caption(region_id: str, household: str | None) -> tuple[str, str]:
    """역세권 통근 씬 캡션 — 실측 통근분 있으면 그대로 인용(없으면 '도보권'까지만, 숫자 지어내지 않음)."""
    wp = profile_for(household).get("workplace")
    if wp:
        tr = trades_store.read_region_transit(region_id, wp["name"])
        if tr and tr.get("minutes"):
            return "지하철역 도보권", f"{wp['name']} 통근 실측 약 {tr['minutes']}분"
    return "지하철역 도보권", "출근길도 가볍게"


def _dynamic_scenes(region_id: str, household: str | None, lead_signal: str | None) -> list[dict] | None:
    """region_enrich.yaml 태그 기반 고정 3씬 조립. 태그 정보가 아예 없으면 None(→ base 폴백)."""
    enrich = molit.load_enrich().get(region_id)
    if not enrich:
        return None
    raw_tags = enrich.get("tags") or []
    if not raw_tags:
        return None
    normalized = {_TAG_ALIASES.get(t, t) for t in raw_tags}
    has_transit = "초역세권" in normalized or "역세권" in normalized

    scenes: list[dict] = []
    if has_transit:
        cap1, cap2 = _commute_caption(region_id, household)
        scenes.append(
            {
                "time": _TIMES_WITH_COMMUTE[0],
                "emoji": "🚇",
                "visual": _scene_image_url(region_id, _COMMUTE_SLUG),
                "caption1": cap1,
                "caption2": cap2,
                "basis": "역세권(카카오맵 최근접역 기준)",
            }
        )
        content = _pick_content_tags(raw_tags, lead_signal, 2)
        times = _TIMES_WITH_COMMUTE[1:]
    else:
        content = _pick_content_tags(raw_tags, lead_signal, 3)
        times = _TIMES_NO_COMMUTE

    if not content and not scenes:
        return None  # 통근도 상권 태그도 없음 — 정직하게 base로 폴백

    for time, tag in zip(times, content):
        meta = _TAG_SCENE_META[tag]
        scenes.append(
            {
                "time": time,
                "emoji": meta["emoji"],
                "visual": _scene_image_url(region_id, _TAG_SLUG[tag]),
                "caption1": meta["caption1"],
                "caption2": "",
                "basis": f"{tag} (상권 실측·소상공인시장진흥공단)",
            }
        )
    return scenes or None


def _select(branch: str, region_id: str, household: str | None, lead_signal: str | None) -> list[dict]:
    reg = _registry()
    override = (reg.get("regions") or {}).get(region_id, {}).get(branch)
    if override:
        return override  # 기존 수기 커스텀 씬(월세 3개 동)은 그대로 우선
    dynamic = _dynamic_scenes(region_id, household, lead_signal) if region_id else None
    return dynamic or reg["base"][branch]


def run(
    branch: Branch,
    region_id: str = "",
    *,
    household: str | None = None,
    lead_signal: str | None = None,
) -> SimulateResponse:
    reg = _registry()
    scenes = [Scene(**s) for s in _select(branch, region_id, household, lead_signal)]
    monthly_cost = reg["monthly_cost"][branch]
    return SimulateResponse(scenes=scenes, monthlyCost=monthly_cost)


# ── 개인화 라이프스타일 내레이션 ('온라인 발품') ──────────────────────────
@lru_cache(maxsize=1)
def _profiles() -> dict:
    with _PROFILES_YAML.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def profile_for(household: str | None) -> dict:
    """가구 유형 → 소비 프로필(없으면 default). 실서비스는 KB 데이터로 교체."""
    p = _profiles()
    return p["profiles"].get(household or "", p["default"])


@lru_cache(maxsize=1)
def _region_facts_yaml() -> dict:
    """수기 지역 데이터(주로 transport) — data/region_facts.yaml. 없으면 {}."""
    if not _REGION_FACTS_YAML.exists():
        return {}
    with _REGION_FACTS_YAML.open(encoding="utf-8") as f:
        return (yaml.safe_load(f) or {}).get("facts", {}) or {}


def _facts_for(region_id: str | None) -> dict:
    """지역 대표 데이터 병합: DB(상권 자동집계 grocery/dining_cafe/leisure) + YAML(수기 transport 등).

    - DB(region_facts, refresh_regions.py가 채움)가 grocery/dining_cafe/leisure를 덮는다(자동·최신).
    - YAML은 transport·price_level·notes 등 수기 값을 유지.
    - 둘 다 없으면 {} → 발품은 name+tags 폴백.
    """
    yaml_f = _region_facts_yaml().get(region_id or "", {})
    db_f = trades_store.read_region_facts(region_id or "")  # {field: [값...]} (DB 없으면 {})
    return {**yaml_f, **db_f}


def _facts_block(region_id: str | None) -> str:
    """regionId → 프롬프트에 넣을 '동네 대표 정보' 블록(없으면 빈 문자열)."""
    f = _facts_for(region_id)
    if not f:
        return ""
    lines = []
    for key, label in (
        ("transport", "교통"),
        ("grocery", "장보기"),
        ("dining_cafe", "카페·먹거리"),
        ("leisure", "여가"),
        ("academy", "학원"),
    ):
        if f.get(key):
            lines.append(f"- {label}: {', '.join(f[key])}")
    if f.get("price_level"):
        lines.append(f"- 물가 체감: {f['price_level']}")
    if f.get("notes"):
        lines.append(f"- 참고: {f['notes']}")
    return ("동네 대표 정보:\n" + "\n".join(lines) + "\n") if lines else ""


def _region_of(ctx: dict) -> dict:
    """ctx의 region(dict) 우선, 없으면 regionName(str)만으로 최소 구성."""
    reg = ctx.get("region")
    if isinstance(reg, dict):
        return reg
    name = ctx.get("regionName")
    return {"name": name} if name else {}


_BRANCH_TRADE = {"매매": "sale", "이사": "jeonse", "갱신": "jeonse"}


def _transit_fact(reg: dict, household: str | None, wfh: bool = False) -> str:
    """동네 center → 가구별 대표 직장까지 통근시간 발품(ODsay 실측 or 직선거리 예상치).

    좌표·직장 없으면 ''. 폴백(예상치)은 순수계산이라 런타임/오프라인 안전.
    wfh(재택 확정)면 통근을 '참고'로 격하(값은 유지, 앞세우지 않음, G3).
    """
    lat, lng = reg.get("lat"), reg.get("lng")
    wp = profile_for(household).get("workplace")
    if not (lat and lng and wp):
        return ""
    # 런타임은 DB 캐시(refresh가 ODsay 실측 적재)만 읽고, 없으면 순수 추정 — 라이브 호출·오프라인 안전.
    c = trades_store.read_region_transit(reg.get("id") or "", wp["name"]) or transit.estimate(
        float(lat), float(lng), wp["lat"], wp["lng"]
    )
    tr = f", 환승 {c['transfers']}회" if c.get("transfers") else ""
    tag = "(예상)" if c.get("estimated") else ""
    if wfh:
        # 재택 확정 → 통근은 참고. 프롬프트가 앞세우지 않도록 라벨.
        return f"통근(참고·재택 반영): {wp['name']} 근무 시 대중교통 약 {c['minutes']}분{tr}{tag}"
    # 직장은 '가정'(모를 수 있음) → 조건부로. 프롬프트가 '~라면'으로 서술.
    return f"통근(가정): {wp['name']} 근무 시 대중교통 약 {c['minutes']}분{tr}{tag}"


def _budget_cap(ctx: dict, reg: dict) -> int | None:
    """발품 실거래 캡(예산 상한). ctx.budget(프론트가 고른 갈래 예산) 우선, 없으면 region에서 유추.

    region.surplus = budget - midPrice 이므로 midPrice+surplus로 복원(있을 때만). 둘 다 없으면 None(캡 없음).
    """
    b = ctx.get("budget")
    if isinstance(b, (int, float)) and b > 0:
        return int(b)
    mid, surplus = reg.get("midPrice"), reg.get("surplus")
    if isinstance(mid, (int, float)) and mid > 0 and isinstance(surplus, (int, float)):
        return int(mid + surplus)
    return None


def _trade_fact(region_name: str, branch: str, max_price: int | None = None) -> str:
    """동네 실거래 사례 1건 → '최근 실거래' 근거(국토부 실데이터). 없으면 ''.

    max_price(예산 상한)를 주면 그 이하 거래에서 선정(발품이 예산 초과 매물을 앞세우지 않게, G2).
    상한 이하 표본이 없어 초과 사례를 쓰면 '예산 상위 평형 기준'을 명시한다.
    """
    dong = (region_name or "").split()[-1]  # "마포구 망원동" → "망원동"
    trade_type = _BRANCH_TRADE.get(branch or "", "sale")
    t = trades_store.sample_trade(dong, trade_type, max_price=max_price)
    if not t or not t.get("price"):
        return ""
    eok = round(t["price"] / 100_000_000, 1)
    area = f"전용 {round(t['area_m2'])}㎡ " if t.get("area_m2") else ""
    kind = "매매" if trade_type == "sale" else "전세"
    over = " · 예산 상위 평형 기준" if t.get("overBudget") else ""
    return f"최근 실거래(국토부): {area}{kind} {eok}억 ({t['deal_ym']}){over}"


def build_lifestyle_prompt(ctx: dict) -> tuple[str, str]:
    """(system, user) — 동네 실데이터 + 소비 프로필로 그라운딩. 숫자 단정 금지."""
    reg = _region_of(ctx)
    fin = ctx.get("finance") or {}
    prof = profile_for(fin.get("household"))
    name = reg.get("name") or "이 동네"
    tags = ", ".join(reg.get("tags") or []) or "정보 제한"
    branch = ctx.get("branch") or ""
    facts = _facts_block(reg.get("id"))  # 자동 상권(DB) + 수기(YAML) 병합
    trade = _trade_fact(name, branch, _budget_cap(ctx, reg))  # 실거래 사례(예산 이하 우선, G2)
    trade_line = f"{trade}\n" if trade else ""
    wfh = bool(ctx.get("wfh"))  # 재택 확정 → 통근 격하(G3)
    commute = _transit_fact(reg, fin.get("household"), wfh)  # 직장까지 통근시간
    commute_line = f"{commute}\n" if commute else ""
    jr = reg.get("jeonseRatio")
    jeonse_line = (
        f"전세가율(실거래): {round(jr['ratio'] * 100)}% — {jr['label']}\n" if (jr and branch == "이사") else ""
    )
    system = _profiles()["base"].strip()
    user = (
        f"동네: {name}\n"
        f"동네 특징(태그): {tags}\n"
        f"{facts}"
        f"{commute_line}"
        f"{trade_line}"
        f"{jeonse_line}"
        f"검토 갈래: {branch}\n"
        f"이 사용자 소비 성향: {', '.join(prof.get('traits', []))}\n"
        f"관심 키워드: {', '.join(prof.get('keywords', []))}\n"
        "→ 위 정보로 '이 동네에서의 하루'를 2~3문장으로 그려라. **facts(통근·상권·실거래)를 먼저 앞세운다.** "
        "'통근(가정)' 정보가 있으면 '만약 …로 통근한다면 약 N분' 식 조건부로 녹여라. "
        + ("**단 통근이 '참고·재택 반영'이면 앞세우지 말고 맨 뒤에 가볍게만 언급하라.** " if wfh else "")
        + "**소비 성향 × 상권 facts를 연결하는 문장을 최소 1개 넣어라**(예: '배달 지출이 많은 편이면 "
        "음식점 N곳이 가까워 선택지가 넓어요'). 단 그 N은 위 facts에 실제 있는 값만 인용한다. "
        "**유보·확인필요 표현은 전체에서 한 번 이내** — 없는 정보는 언급 말고 있는 facts로만 말해라. "
        "**가격·비용(아메리카노 N원, 점심 N원대, 월세 N만 등)과 주차·혼잡·무료·영업시간·반려동물 허용·"
        "가게 상태(노포/새 가게/활기/즐비/저렴) 같은 단정은 facts에 없으면 절대 지어내지 마라.** "
        "'최근 실거래'는 국토부 실데이터이니 그대로 한 번 언급해도 좋다(그 외 금액·개수 단정 금지)."
    )
    return system, user


def lifestyle_fallback(ctx: dict) -> str:
    """llm 비활성 시 결정론 폴백 — 동네명·태그·소비성향을 조합한 안전 문장.

    ctx.trait(프로필이 확정한 소비 신호: 실측>진술>세그먼트)가 오면 그걸 쓴다 — 리포트 요약과
    프로필 칩의 소비 문구를 일치시키기 위함(L5.2). 없으면 세그먼트 traits 기본값.
    """
    reg = _region_of(ctx)
    fin = ctx.get("finance") or {}
    prof = profile_for(fin.get("household"))
    name = reg.get("name") or "이 동네"
    tag = (reg.get("tags") or ["생활 편의"])[0]
    trait = ctx.get("trait") or (prof.get("traits") or ["생활 편의 중심 소비"])[0]
    return (
        f"{name}로 옮기면 '{tag}' 분위기 속에서 지금의 소비 습관({trait})을 자연스럽게 이어가기 좋아요. "
        "실제 동선·물가는 상담에서 더 자세히 확인해요."
    )


def _facts_used(ctx: dict) -> list[dict]:
    """발품에 주입된 facts 목록 + 출처 — 관측용('지어낸 것 0' 증명)."""
    reg = _region_of(ctx)
    fin = ctx.get("finance") or {}
    out: list[dict] = []
    f = _facts_for(reg.get("id"))
    for key, src in (
        ("dining_cafe", "상권(소상공인API)"),
        ("grocery", "상권(소상공인API)"),
        ("leisure", "상권(소상공인API)"),
        ("academy", "상권(소상공인API)"),
    ):
        if f.get(key):
            out.append({"type": src, "field": key, "value": f[key][:2]})
    commute = _transit_fact(reg, fin.get("household"))
    if commute:
        out.append({"type": "통근(ODsay)", "value": commute})
    trade = _trade_fact(reg.get("name") or "", ctx.get("branch") or "", _budget_cap(ctx, reg))
    if trade:
        out.append({"type": "실거래(국토부)", "value": trade})
    jr = reg.get("jeonseRatio")  # 전세 후보면 Region에 부착됨(표본<5면 없음)
    if jr and ctx.get("branch") == "이사":
        out.append(
            {
                "type": "전세가율(실거래)",
                "value": f"전세가율 {round(jr['ratio'] * 100)}% — {jr['label']} ({jr['basis']})",
            }
        )
    return out


def narrate_lifestyle(ctx: dict) -> str:
    """동네 실데이터 + 소비 프로필 → 생성형 내레이션(llm) / 폴백(결정론)."""
    from ..core.tracing import span_update

    system, user = build_lifestyle_prompt(ctx)
    reg = _region_of(ctx)
    fin = ctx.get("finance") or {}
    # 관측: 주입된 facts(출처 포함) + 소비성향. verify/LLM 사용여부는 generate가 같은 span에 기록.
    span_update(
        input={
            "region": reg.get("name"),
            "facts": _facts_used(ctx),
            "traits": profile_for(fin.get("household")).get("traits", []),
        }
    )
    # O2-1: 숫자 verify 활성화 — 생성문의 모든 숫자는 facts 프롬프트(user)에 등장한 값의 부분집합이어야 한다.
    # (numbers_grounded 실패 시 core.llm.generate가 재생성 2회 → 폴백. 그동안 미전달로 잠들어 있던 검증을 켬)
    from ..core.verify import _numbers

    allowed_numbers = _numbers(user)
    text = generate(system=system, user=user, fallback=lambda: lifestyle_fallback(ctx), allowed_numbers=allowed_numbers)
    span_update(output={"narration": text})
    return text
