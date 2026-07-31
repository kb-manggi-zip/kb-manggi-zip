"""region_enrich.yaml의 tags/source 자동 채우기 (오프라인, 실 API 호출).

⚠️ 서버 런타임은 이 스크립트를 실행하지 않는다 — 결과(region_enrich.yaml)만 읽는다.
대상: 80개 동 전체(기존 수기 7개 동 포함) — 자동 산출 태그를 기존 수기 태그와 합집합으로 병합.

전부 "80개 동 중 상위 25%" 상대 기준으로 통일(2026-07-31, 절대 임계값 방식에서 변경):
  1) 상권형 태그(SBIZ 반경상가 카운트, trades_store.region_facts) — 카운트 상위 25%(3분위 이상).
     음식점·카페 밀집 / 마트·편의점 밀집 / 여가시설 밀집 / 학원가
  2) 위치형 태그(카카오맵 Local API, app/tools/kakao.py) — 최근접 지점까지 거리 상위 25%(1분위 이하, 가장 가까운 쪽).
     "역세권"은 실제로 흔한 표현(반경 500m=도보10분이 일반적 정의)이라 절대기준으로 하면 서울 6개구에선
     변별력이 없어짐(64%가 해당) → 상대기준으로 바꾸며 원래 뜻과 구분해 "초역세권"으로 명명.
     "공원 인접"은 카카오에 공원 전용 카테고리가 없어(키워드검색만 가능) 반경 안에 아무거나 하나 걸리면
     참이 되는 게 원래도 부정확했음(97%) → 상대기준으로 교체(태그명은 유지).

실행: python scripts/refresh/build_region_tags.py
"""

import logging
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # backend/

from app.core.config import BACKEND_ROOT  # noqa: E402
from app.tools import kakao, trades_store  # noqa: E402

log = logging.getLogger("build_region_tags")

SBIZ_TAGS = [
    ("dining_cafe", "음식점·카페 밀집"),
    ("grocery", "마트·편의점 밀집"),
    ("leisure", "여가시설 밀집"),
    ("academy", "학원가"),
]
SUBWAY_SEARCH_RADIUS = 3000  # m — 최근접역 순위 산출용(넉넉하게, 서울 6구엔 항상 걸림)
PARK_SEARCH_RADIUS = 3000

HEADER = """# 동 → 좌표/태그 보강 (실거래엔 좌표·태그가 없음)
# 6개구 80개동 전체 좌표를 카카오맵 지오코딩 API로 재조회함 (가나다순 정렬).
# tags/source: scripts/refresh/build_region_tags.py로 80개 동 전체 자동 산출(2026-07-31) —
#   상권형(SBIZ 카운트 상위25%) + 위치형(카카오맵 최근접 지하철역·공원 거리 상위25%).
#   기존 수기 7개 동은 그 태그를 유지한 채 자동 산출 결과와 합집합으로 병합.
# (⚠️ 임의 작문 금지 — 확인 가능한 것만 채울 것).
"""


def _facts_count(region_id: str, field: str) -> int | None:
    return trades_store.read_region_fact_counts(region_id).get(field)


def _nearest_m(docs: list[dict]) -> float | None:
    return min((float(d["distance"]) for d in docs), default=None)


def _quartile_high(values: list[float]) -> float:
    """상위 25% 임계값(3분위) — 이 값 이상이면 태그."""
    return statistics.quantiles(sorted(values), n=4)[2]


def _quartile_low(values: list[float]) -> float:
    """최근접 상위 25% 임계값(1분위) — 이 값 이하(더 가까움)면 태그."""
    return statistics.quantiles(sorted(values), n=4)[0]


def main() -> None:
    path = BACKEND_ROOT / "data" / "region_enrich.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    entries = list(data.items())

    # ── 1) 원자료 수집(80개 동 전체) ──────────────────────────────────
    counts: dict[str, dict[str, int | None]] = {}
    subway_dist: dict[str, float | None] = {}
    park_dist: dict[str, float | None] = {}
    for umd, v in entries:
        counts[umd] = {field: _facts_count(v["id"], field) for field, _ in SBIZ_TAGS}
        subway_dist[umd] = _nearest_m(kakao.nearby_subway(v["lat"], v["lng"], radius=SUBWAY_SEARCH_RADIUS))
        park_dist[umd] = _nearest_m(kakao.nearby_park(v["lat"], v["lng"], radius=PARK_SEARCH_RADIUS))
        time.sleep(0.2)
        log.info("%s: 상권=%s 최근접역=%sm 최근접공원=%sm", umd, counts[umd], subway_dist[umd], park_dist[umd])

    # ── 2) 임계값(상위 25%) 산출 ──────────────────────────────────────
    sbiz_th = {
        field: _quartile_high([c[field] for c in counts.values() if c[field] is not None]) for field, _ in SBIZ_TAGS
    }
    subway_th = _quartile_low([d for d in subway_dist.values() if d is not None])
    park_th = _quartile_low([d for d in park_dist.values() if d is not None])
    log.info("임계값 — SBIZ: %s / 최근접역<=%.0fm / 최근접공원<=%.0fm", sbiz_th, subway_th, park_th)

    # ── 3) 태그 부여 + 기존 수기 태그와 병합 ──────────────────────────
    today = datetime.now().strftime("%Y-%m-%d")
    for umd, v in entries:
        auto_tags: list[str] = []
        auto_source: list[str] = []

        for field, tag in SBIZ_TAGS:
            n = counts[umd][field]
            if n is not None and n >= sbiz_th[field]:
                auto_tags.append(tag)
                auto_source.append(f"{tag}: {field} {n}곳(80개 동 중 상위25%, 기준 {sbiz_th[field]:.0f}+)")

        sd = subway_dist[umd]
        if sd is not None and sd <= subway_th:
            auto_tags.append("초역세권")
            auto_source.append(f"초역세권: 최근접역 {sd:.0f}m(80개 동 중 최근접 상위25%, 기준 {subway_th:.0f}m 이내)")

        pd = park_dist[umd]
        if pd is not None and pd <= park_th:
            auto_tags.append("공원 인접")
            auto_source.append(f"공원 인접: 최근접공원 {pd:.0f}m(80개 동 중 최근접 상위25%, 기준 {park_th:.0f}m 이내)")

        existing_tags = v.get("tags") or []
        existing_source = v.get("source") or ""
        v["tags"] = existing_tags + [t for t in auto_tags if t not in existing_tags]
        parts = ([existing_source] if existing_source else []) + auto_source
        v["source"] = (" / ".join(parts) + f" — 자동 산출({today})") if auto_source else existing_source

    dumped = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
    path.write_text(HEADER + "\n" + dumped, encoding="utf-8")
    log.info("완료: 80개 동 전체 자동 산출 + 수기 병합 (%s)", path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
