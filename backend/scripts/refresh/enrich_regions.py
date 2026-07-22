"""region_enrich.yaml 보강 — 카카오 지오코딩으로 좌표 전체 재조회.

실행: python scripts/refresh/enrich_regions.py   (.env 에 KAKAO_API_KEY 필요)

- 80개 동(6개구) 전체 좌표를 카카오 지오코딩 API로 재조회해서 통일된 소스로 맞춘다.
- 기존 8개 수기 항목의 tags(사람이 확인한 역세권/상권 등)는 그대로 유지, 좌표만 갱신.
- 새로 추가되는 72개는 tags 빈 배열(임의 작문 금지 원칙 유지), source는 자동 조회로 표기.
"""
import os
import sqlite3
import sys
import time
from pathlib import Path

import httpx
import yaml

BACKEND_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402

GU_MAP = {
    "11440": "마포구", "11380": "은평구", "11320": "도봉구",
    "11290": "성북구", "11350": "노원구", "11260": "중랑구",
}

ENRICH_PATH = BACKEND_ROOT / "data" / "region_enrich.yaml"
DB_PATH = BACKEND_ROOT / "data" / "trades.demo.db"


def geocode(query: str, api_key: str) -> tuple[float, float] | None:
    r = httpx.get(
        "https://dapi.kakao.com/v2/local/search/address.json",
        params={"query": query},
        headers={"Authorization": f"KakaoAK {api_key}"},
        timeout=5.0,
    )
    r.raise_for_status()
    docs = r.json().get("documents", [])
    if not docs:
        return None
    d = docs[0]
    return float(d["y"]), float(d["x"])  # lat, lng


def main() -> None:
    api_key = os.environ.get("KAKAO_API_KEY") or getattr(settings, "kakao_api_key", None)
    if not api_key:
        raise RuntimeError(".env 에 KAKAO_API_KEY 가 필요합니다.")

    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT DISTINCT sigungu_code, umd_name FROM trades").fetchall()
    all_dongs = sorted(set(rows))
    print(f"전체 대상: {len(all_dongs)}개 동 (좌표 전체 재조회)")

    with open(ENRICH_PATH, encoding="utf-8") as f:
        old_enrich = yaml.safe_load(f) or {}
    existing_names = set(old_enrich.keys())

    new_enrich: dict = {}
    ok, fail = 0, []
    for sigungu_code, umd in all_dongs:
        gu = GU_MAP.get(sigungu_code, "")
        query = f"서울 {gu} {umd}"
        try:
            coord = geocode(query, api_key)
        except httpx.HTTPStatusError as e:
            print(f"  ✗ {query}: HTTP {e.response.status_code}")
            fail.append(umd)
            coord = None

        is_manual = umd in existing_names
        old = old_enrich.get(umd, {})

        if coord is None:
            if is_manual:
                # 재조회 실패 시 기존 수기 좌표 보존
                new_enrich[umd] = old
                fail.append(umd)
            else:
                print(f"  ✗ {query}: 결과 없음 (제외)")
                fail.append(umd)
            continue

        lat, lng = coord
        new_enrich[umd] = {
            "id": old.get("id", umd),
            "lat": round(lat, 4),
            "lng": round(lng, 4),
            "tags": old.get("tags", []),  # 수기 항목은 기존 tags 유지, 신규는 빈 배열
            "source": (
                old.get("source", "") + " / 좌표는 카카오맵 지오코딩 API로 재조회"
                if is_manual
                else "카카오맵 지오코딩 API 자동 조회 (좌표만, tags 미확인 — 임의 작문 금지 원칙상 비움)"
            ),
        }
        ok += 1
        time.sleep(0.05)  # 쿼터 여유

    with open(ENRICH_PATH, "w", encoding="utf-8") as f:
        f.write(
            "# 동 → 좌표/태그 보강 (실거래엔 좌표·태그가 없음)\n"
            "# 6개구 80개동 전체 좌표를 카카오맵 지오코딩 API로 재조회해 통일함.\n"
            "# 원래 수기로 채워졌던 8개 동은 tags(역세권/상권 등, 사람이 확인)는 그대로 유지, 좌표만 갱신.\n"
            "# 나머지 신규 72개는 tags 비움 (⚠️ 임의 작문 금지 — 확인 가능한 것만 채울 것).\n\n"
        )
        yaml.safe_dump(new_enrich, f, allow_unicode=True, sort_keys=False)

    print(f"완료: {ok}개 성공, {len(fail)}개 실패")
    if fail:
        print("실패 목록:", fail)


if __name__ == "__main__":
    main()
