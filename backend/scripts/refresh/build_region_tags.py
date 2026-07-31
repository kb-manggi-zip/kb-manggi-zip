"""region_enrich.yaml의 tags/source 자동 채우기 (오프라인, 실 API 호출).

⚠️ 서버 런타임은 이 스크립트를 실행하지 않는다 — 결과(region_enrich.yaml)만 읽는다.
대상: tags가 비어있는 동만(기존 수기 채운 동은 그대로 유지).

두 갈래 근거:
  1) 상권형 태그 — 이미 수집된 trades_store.region_facts(SBIZ) 카운트를 3분위(상위 25%) 기준으로 태깅.
     임계값은 81개 동 실측 분포에서 산출(2026-07-31): dining_cafe>=298 · grocery>=208 · leisure>=48 · academy>=86.
  2) 위치형 태그 — 카카오맵 Local API(app/tools/kakao.py): 반경 500m 내 지하철역 → "역세권",
     반경 800m 내 공원(키워드검색) → "공원 인접".

실행: python scripts/refresh/build_region_tags.py
"""

import logging
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # backend/

from app.core.config import BACKEND_ROOT  # noqa: E402
from app.tools import kakao, trades_store  # noqa: E402

log = logging.getLogger("build_region_tags")

# field → (임계값, 태그명). 81개 동 SBIZ 실측 분포 3분위(상위 25%) 기준.
THRESHOLDS: list[tuple[str, int, str]] = [
    ("dining_cafe", 298, "카페거리"),
    ("grocery", 208, "마트·편의점 밀집"),
    ("leisure", 48, "여가시설 밀집"),
    ("academy", 86, "학원가"),
]

HEADER = """# 동 → 좌표/태그 보강 (실거래엔 좌표·태그가 없음)
# 6개구 80개동 전체 좌표를 카카오맵 지오코딩 API로 재조회함 (가나다순 정렬).
# tags/source: 수기 7개 동은 그대로 유지. 나머지는 scripts/refresh/build_region_tags.py로
# 자동 산출(2026-07-31) — 상권형(SBIZ 상위25%) + 위치형(카카오맵 지하철역/공원 반경검색).
# (⚠️ 임의 작문 금지 — 확인 가능한 것만 채울 것).
"""


def _facts_count(region_id: str, field: str) -> int | None:
    return trades_store.read_region_fact_counts(region_id).get(field)


def build_tags(region_id: str, lat: float, lng: float) -> tuple[list[str], str]:
    tags: list[str] = []
    sources: list[str] = []

    for field, th, tag in THRESHOLDS:
        n = _facts_count(region_id, field)
        if n is not None and n >= th:
            tags.append(tag)
            sources.append(f"{tag}: {field} {n}곳(SBIZ 반경상가 집계, 상위 25%={th}+)")

    subway = kakao.nearby_subway(lat, lng)
    if subway:
        nearest = min(subway, key=lambda d: int(d["distance"]))
        tags.append("역세권")
        sources.append(f"역세권: {nearest['place_name']} {nearest['distance']}m(카카오맵 반경 500m)")

    park = kakao.nearby_park(lat, lng)
    if park:
        nearest = min(park, key=lambda d: int(d["distance"]))
        tags.append("공원 인접")
        sources.append(f"공원 인접: {nearest['place_name']} {nearest['distance']}m(카카오맵 키워드검색 반경 800m)")

    source = (" / ".join(sources) + f" — 자동 산출 ({datetime.now().strftime('%Y-%m-%d')})") if sources else ""
    return tags, source


def main() -> None:
    path = BACKEND_ROOT / "data" / "region_enrich.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    filled = skipped = 0
    for umd, v in data.items():
        if v.get("tags"):
            skipped += 1
            continue
        tags, source = build_tags(v["id"], v["lat"], v["lng"])
        v["tags"] = tags
        v["source"] = source
        filled += 1
        log.info("%s(%s): %s", umd, v["id"], tags)
        time.sleep(0.2)

    dumped = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
    path.write_text(HEADER + "\n" + dumped, encoding="utf-8")
    log.info("완료: %d개 동 자동 채움, %d개 동 기존 수기 유지 (%s)", filled, skipped, path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
