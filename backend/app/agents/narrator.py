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
from ..tools import trades_store

_SCENES_YAML = Path(__file__).parent / "scenes.yaml"
_PROFILES_YAML = Path(__file__).parent / "spending_profiles.yaml"
_REGION_FACTS_YAML = BACKEND_ROOT / "data" / "region_facts.yaml"


@lru_cache(maxsize=1)
def _registry() -> dict:
    with _SCENES_YAML.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _select(branch: str, region_id: str) -> list[dict]:
    reg = _registry()
    override = (reg.get("regions") or {}).get(region_id, {}).get(branch)
    return override or reg["base"][branch]


def run(branch: Branch, region_id: str = "") -> SimulateResponse:
    reg = _registry()
    scenes = [Scene(**s) for s in _select(branch, region_id)]
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


def build_lifestyle_prompt(ctx: dict) -> tuple[str, str]:
    """(system, user) — 동네 실데이터 + 소비 프로필로 그라운딩. 숫자 단정 금지."""
    reg = _region_of(ctx)
    fin = ctx.get("finance") or {}
    prof = profile_for(fin.get("household"))
    name = reg.get("name") or "이 동네"
    tags = ", ".join(reg.get("tags") or []) or "정보 제한"
    branch = ctx.get("branch") or ""
    facts = _facts_block(reg.get("id"))  # 팀원이 채운 지역 데이터(있으면 더 구체적)
    system = _profiles()["base"].strip()
    user = (
        f"동네: {name}\n"
        f"동네 특징(태그): {tags}\n"
        f"{facts}"
        f"검토 갈래: {branch}\n"
        f"이 사용자 소비 성향: {', '.join(prof.get('traits', []))}\n"
        f"관심 키워드: {', '.join(prof.get('keywords', []))}\n"
        "→ 위 정보만 근거로 '이 동네에서의 하루'를 2~3문장으로 그려라. 주어지지 않은 금액·개수는 단정하지 마라."
    )
    return system, user


def lifestyle_fallback(ctx: dict) -> str:
    """llm 비활성 시 결정론 폴백 — 동네명·태그·소비성향을 조합한 안전 문장."""
    reg = _region_of(ctx)
    fin = ctx.get("finance") or {}
    prof = profile_for(fin.get("household"))
    name = reg.get("name") or "이 동네"
    tag = (reg.get("tags") or ["생활 편의"])[0]
    trait = (prof.get("traits") or ["생활 편의 중심 소비"])[0]
    return (
        f"{name}로 옮기면 '{tag}' 분위기 속에서 지금의 소비 습관({trait})을 자연스럽게 이어가기 좋아요. "
        "실제 동선·물가는 상담에서 더 자세히 확인해요."
    )


def narrate_lifestyle(ctx: dict) -> str:
    """동네 실데이터 + 소비 프로필 → 생성형 내레이션(llm) / 폴백(결정론)."""
    system, user = build_lifestyle_prompt(ctx)
    return generate(system=system, user=user, fallback=lambda: lifestyle_fallback(ctx))
