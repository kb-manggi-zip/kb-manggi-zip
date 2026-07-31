"""카카오맵 Local API — 반경 내 지하철역/공원 존재 여부 (.env KAKAO_API_KEY).

역세권: category_group_code=SW8(지하철역) 카테고리 검색 — 카카오 공식 카테고리라 정확.
공원: 카카오엔 "공원" 전용 카테고리가 없어 키워드 검색("공원")만 가능 — category_name이
      "여행 > 공원"으로 시작하는 것만 인정(무관한 업체명 오매칭 방지). 지하철역보다 부정확할 수 있음.

⚠️ 오프라인 스크립트(scripts/refresh/)에서만 호출 — 서버 런타임은 이 모듈을 쓰지 않는다(쿼터 보호).
"""

import logging

import requests

from ..core.config import settings

log = logging.getLogger("kb.kakao")

BASE = "https://dapi.kakao.com/v2/local/search"


def _headers() -> dict:
    return {"Authorization": f"KakaoAK {settings.kakao_api_key}"}


def nearby_subway(lat: float, lng: float, radius: int = 500) -> list[dict]:
    """반경(m) 내 지하철역 목록(카테고리 검색, 정확). 실패/키없음 → []."""
    if not settings.kakao_api_key:
        return []
    try:
        resp = requests.get(
            f"{BASE}/category.json",
            headers=_headers(),
            params={"category_group_code": "SW8", "x": lng, "y": lat, "radius": radius},
            timeout=8,
        )
        return resp.json().get("documents", [])
    except Exception as e:
        log.warning("카카오 지하철역 검색 실패(%s, %s): %s", lat, lng, e)
        return []


def nearby_park(lat: float, lng: float, radius: int = 800) -> list[dict]:
    """반경(m) 내 공원 목록(키워드 검색 "공원", category_name으로 필터링). 실패/키없음 → []."""
    if not settings.kakao_api_key:
        return []
    try:
        resp = requests.get(
            f"{BASE}/keyword.json",
            headers=_headers(),
            params={"query": "공원", "x": lng, "y": lat, "radius": radius},
            timeout=8,
        )
        docs = resp.json().get("documents", [])
        return [d for d in docs if d.get("category_name", "").startswith("여행 > 공원")]
    except Exception as e:
        log.warning("카카오 공원 검색 실패(%s, %s): %s", lat, lng, e)
        return []
