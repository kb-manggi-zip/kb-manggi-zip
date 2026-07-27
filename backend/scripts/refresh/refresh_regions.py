"""소상공인 상권정보 → region_facts 자동 수집 (오프라인) → SQLite(trades.db).

⚠️ 외부 API를 때리는 곳(refresh_deals와 동일 원칙). 서버 런타임은 이걸 실행하지 않는다.
런타임 narrator는 DB의 region_facts를 읽고 region_facts.yaml(transport 수기)와 병합한다.

실행:  python scripts/refresh/refresh_regions.py     (.env 에 SBIZ_API_KEY 필요, Decoding 키)
사용 API: 소상공인시장진흥공단 상가정보 '반경상가'(=/storeListInRadius, 개별 업소 목록)
집계: 반경 500m 내 업소를 업종 대분류(indsLclsNm)로 카운트
  · grocery     ← '소매'      (마트·편의점·종합소매)
  · dining_cafe ← '음식'      (한식·카페·제과 등 전부)
  · leisure     ← '여가/스포츠/관광/오락'
결과: trades_store.region_facts (region_id, field, value_json, count, source, collected_at)

※ 필드명(indsLclsNm 등)은 PublicDataReader.SmallShop '반경상가' columns에서 확인(추측 아님).
   대분류 명칭은 substring 매칭(명칭 변형에 견고). 실행 후 개수가 상식적인지 눈으로 확인할 것.
"""

import logging
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # backend/

from app.core.config import settings  # noqa: E402
from app.tools import trades_store  # noqa: E402

log = logging.getLogger("refresh_regions")

RADIUS = 500  # m
SERVICE = "반경상가"  # SmallShop → /storeListInRadius

# 데모 9개 지역 (프론트 src/data/regions.ts 의 Region.id ↔ 동·좌표)
#   6구 밖(서대문 홍제동)도 있어 enrich.yaml(6구)로는 부족 → 여기 명시.
DEMO_REGIONS = [
    ("mapo", "합정동", 37.5498, 126.9137),
    ("eunpyeong", "녹번동", 37.6059, 126.9286),
    ("dobong", "창동", 37.6533, 127.0473),
    ("seongbuk", "길음동", 37.6038, 127.0193),
    ("nowon", "상계동", 37.6550, 127.0631),
    ("jungnang", "면목동", 37.5780, 127.0924),
    ("mapo-m", "망원동", 37.5561, 126.9026),
    ("seodaemun-m", "홍제동", 37.5893, 126.9392),
    ("seongbuk-m", "보문동", 37.5893, 127.0192),
]


def classify(lcls: str) -> str | None:
    """업종 대분류명 → region_facts field (매칭 안 되면 None)."""
    if "소매" in lcls:
        return "grocery"
    if "음식" in lcls:
        return "dining_cafe"
    if any(k in lcls for k in ("여가", "스포츠", "관광", "오락")):
        return "leisure"
    return None


def count_by_field(df) -> dict:
    """반경 업소 DataFrame → {field: 개수}. bizesId 중복 제거."""
    if df is None or getattr(df, "empty", True):
        return {}
    if "bizesId" in df.columns:
        df = df.drop_duplicates(subset=["bizesId"])
    col = "indsLclsNm"
    if col not in df.columns:
        log.error("응답에 '%s' 컬럼 없음. 실제 컬럼=%s (매핑 재확인 필요)", col, list(df.columns))
        return {}
    counts: dict = {}
    for lcls in df[col].dropna():
        f = classify(str(lcls))
        if f:
            counts[f] = counts.get(f, 0) + 1
    return counts


def to_facts(counts: dict) -> dict:
    """{field: 개수} → {field: (값 리스트, 개수)}. 스키마 문구 생성."""
    out: dict = {}
    if counts.get("grocery"):
        out["grocery"] = ([f"반경 {RADIUS}m 내 마트·편의점 {counts['grocery']}곳"], counts["grocery"])
    if counts.get("dining_cafe"):
        n = counts["dining_cafe"]
        out["dining_cafe"] = ([f"음식점·카페 {n}곳" + (" 밀집" if n >= 30 else "")], n)
    if counts.get("leisure"):
        out["leisure"] = ([f"여가시설 {counts['leisure']}곳"], counts["leisure"])
    return out


def inspect_one() -> None:
    """DoD: 실제 응답 키/샘플 출력(추측 금지 검증). `python refresh_regions.py inspect`."""
    key = settings.sbiz_api_key
    if not key:
        log.error("SBIZ_API_KEY 없음 → .env에 추가(Decoding 키) 후 재실행.")
        sys.exit(1)
    from PublicDataReader import SmallShop

    _, name, lat, lng = DEMO_REGIONS[6]  # 망원동
    df = SmallShop(key).get_data(service_name=SERVICE, radius=RADIUS, cx=lng, cy=lat, translate=False)
    print(f"[{name}] 응답 컬럼:", list(df.columns))
    print("샘플 1행:", df.iloc[0].to_dict() if not df.empty else "(0건)")
    print(
        "indsLclsNm 분포:", df["indsLclsNm"].value_counts().to_dict() if "indsLclsNm" in df.columns else "❌ 컬럼없음"
    )


def _collect_region_facts() -> None:
    """상권 집계(SBIZ). 키 없으면 건너뜀."""
    if not settings.sbiz_api_key:
        log.warning("SBIZ_API_KEY 없음 → 상권 수집 건너뜀.")
        return
    from PublicDataReader import SmallShop

    api = SmallShop(settings.sbiz_api_key)
    source = f"소상공인시장진흥공단 상가정보 ({datetime.now().strftime('%Y-%m')})"
    for region_id, name, lat, lng in DEMO_REGIONS:
        try:
            df = api.get_data(service_name=SERVICE, radius=RADIUS, cx=lng, cy=lat, translate=False)
            facts = to_facts(count_by_field(df))
            for field, (values, n) in facts.items():
                trades_store.write_region_facts(region_id, field, values, n, source)
            log.info("[상권] %s(%s): %s", region_id, name, {k: n for k, (_, n) in facts.items()})
        except Exception as e:
            log.warning("[상권] %s(%s) 스킵: %s", region_id, name, e)
        time.sleep(0.3)


def _workplaces() -> list[dict]:
    """spending_profiles의 대표 직장(중복 제거)."""
    from app.agents.narrator import _profiles

    p = _profiles()
    seen: dict = {}
    for prof in list(p.get("profiles", {}).values()) + [p.get("default", {})]:
        wp = prof.get("workplace")
        if wp:
            seen[wp["name"]] = wp
    return list(seen.values())


def _collect_transit() -> None:
    """통근시간(ODsay 실측). 키 없으면 건너뜀(런타임은 예상치 폴백). 실측만 캐싱."""
    if not settings.odsay_api_key:
        log.warning("ODSAY_API_KEY 없음 → 통근 실측 건너뜀(런타임 예상치 사용).")
        return
    from app.tools import transit

    wps = _workplaces()
    for region_id, name, lat, lng in DEMO_REGIONS:
        n = 0
        for wp in wps:
            c = transit.commute(lat, lng, wp["lat"], wp["lng"])
            if not c["estimated"]:  # 실측만 저장(예상치는 런타임이 순수계산)
                trades_store.write_region_transit(region_id, wp["name"], c["minutes"], c["transfers"], c["estimated"])
                n += 1
            time.sleep(0.3)
        log.info("[통근] %s(%s): 실측 %d/%d", region_id, name, n, len(wps))


def main() -> None:
    _collect_region_facts()
    _collect_transit()
    log.info("완료 (DB=%s)", trades_store.resolve_db_path(write=True))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if len(sys.argv) > 1 and sys.argv[1] == "inspect":
        inspect_one()  # 실 응답 키 확인(DoD)
    else:
        main()
