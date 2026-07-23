"""내레이터 에이전트 — 갈래×동네 → 하루 씬 (LLM seam).

지금: catalog fixture 씬 반환 → /api/simulate 동작.
Phase B4: facts(경로·POI·물가) 기반 씬 캡션 생성 + "아낀 돈" 카드.
"""

from ..data.catalog import scenes_for
from ..schemas import Branch, SimulateResponse


def run(branch: Branch, region_id: str) -> SimulateResponse:
    # STUB: LLM 씬 내레이션(Phase B4). 현재는 결정론적 fixture.
    scenes, monthly_cost = scenes_for(branch)
    return SimulateResponse(scenes=scenes, monthlyCost=monthly_cost)
