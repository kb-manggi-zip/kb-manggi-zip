"""대중교통 통근시간 — ODsay 길찾기 (.env ODSAY_API_KEY). 키 없으면 직선거리 예상치 폴백.

원칙(지도 API 폴백과 동일): 키 있으면 실 경로 소요, 없거나 실패하면 **직선거리 기반 예상치 + estimated 플래그**.
런타임에서 직접 호출해도 되지만(폴백은 순수계산), 실 ODsay는 refresh에서 캐싱 권장(쿼터 보호).

⚠️ 실 ODsay 응답 파싱은 공개 스펙 기준으로 작성 → **키 발급 후 실호출로 검증 필요**(추측 최소화).
    확인: python -c "from app.tools import transit; print(transit.commute(37.55,126.90,37.52,126.92))"
"""

import logging
from math import asin, cos, radians, sin, sqrt

from ..core.config import settings

log = logging.getLogger("kb.transit")

ODSAY_URL = "https://api.odsay.com/v1/api/searchPubTransPathT"


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    dlat, dlng = radians(lat2 - lat1), radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return 2 * r * asin(sqrt(a))


def _estimate_minutes(lat1: float, lng1: float, lat2: float, lng2: float) -> int:
    """직선거리 → 도시 대중교통 도어투도어 예상 소요(분). ~22km/h + 도보·대기 12분."""
    km = _haversine_km(lat1, lng1, lat2, lng2)
    return int(round(km / 22 * 60 + 12))


def estimate(from_lat: float, from_lng: float, to_lat: float, to_lng: float) -> dict:
    """순수 직선거리 예상치(외부 호출 없음) — 런타임/오프라인 폴백용. estimated=True 고정."""
    return {
        "minutes": _estimate_minutes(from_lat, from_lng, to_lat, to_lng),
        "transfers": None,
        "estimated": True,
    }


def commute(from_lat: float, from_lng: float, to_lat: float, to_lng: float) -> dict:
    """동네→직장 대중교통 소요. 반환 {minutes, transfers|None, estimated: bool}.

    키 없거나 실패 → estimated=True(직선거리 예상치). 성공 → estimated=False(ODsay 실측).
    """
    fallback = estimate(from_lat, from_lng, to_lat, to_lng)
    if not settings.odsay_api_key:
        return fallback
    try:
        import requests

        resp = requests.get(
            ODSAY_URL,
            params={
                "apiKey": settings.odsay_api_key,
                "SX": from_lng,
                "SY": from_lat,
                "EX": to_lng,
                "EY": to_lat,
                "OPT": 0,
            },
            timeout=8,
        )
        info = resp.json()["result"]["path"][0]["info"]
        transfers = int(info.get("busTransitCount", 0)) + int(info.get("subwayTransitCount", 0)) - 1
        return {"minutes": int(info["totalTime"]), "transfers": max(transfers, 0), "estimated": False}
    except Exception as e:  # 키·쿼터·형식 실패 → 폴백(예상치). 조용히 삼키지 않고 로깅.
        log.warning("ODsay 실패 → 직선거리 예상치 폴백: %s", e)
        return fallback
