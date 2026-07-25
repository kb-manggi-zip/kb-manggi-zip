"""내레이터 에이전트 — 갈래×동네 → 하루 씬.

씬 콘텐츠는 agents/scenes.yaml에서 로드(코드-데이터 분리).
  - regionId가 scenes.yaml `regions`에 있으면 지역별 씬을 우선 사용,
    없으면 branch 기본 씬(base)으로 폴백.
  - 이 덕분에 '월세로'(regionId '…-m')와 '전세로'가 서로 다른 하루로 나온다.
숫자(monthlyCost)는 YAML monthly_cost 값(계산 아님).

# STUB: LLM 씬 내레이션(Phase B4)은 미연동 — 결정론적 YAML fixture.
#        settings.llm_active면 향후 facts(경로·POI·물가) 기반 캡션 생성 예정.
"""

from functools import lru_cache
from pathlib import Path

import yaml

from ..schemas import Branch, Scene, SimulateResponse

_SCENES_YAML = Path(__file__).parent / "scenes.yaml"


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
