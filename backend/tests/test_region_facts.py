"""지역 상권 데이터(발품 그라운딩) — 집계 로직·DB 왕복·narrator 병합.

실 API는 안 때린다(모킹/순수함수). refresh_regions의 순수 집계 함수만 검증.
"""

import importlib.util
from pathlib import Path

import pytest

from app.tools import trades_store


def _refresh():
    """refresh_regions.py를 파일 경로로 로드(스크립트라 패키지 import 불가)."""
    p = Path(__file__).resolve().parents[1] / "scripts" / "refresh" / "refresh_regions.py"
    spec = importlib.util.spec_from_file_location("refresh_regions", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # 모듈 로드(SmallShop import는 main 안에 있어 미실행)
    return mod


def test_classify_by_대분류():
    r = _refresh()
    assert r.classify("소매") == "grocery"
    assert r.classify("음식") == "dining_cafe"
    assert r.classify("관광/여가/오락") == "leisure"
    assert r.classify("스포츠") == "leisure"
    assert r.classify("부동산") is None


def test_count_dedup_and_to_facts():
    pd = pytest.importorskip("pandas")
    r = _refresh()
    df = pd.DataFrame(
        {
            "bizesId": ["1", "2", "2", "3", "9"],  # bizesId 2 중복
            "indsLclsNm": ["음식", "음식", "음식", "소매", "부동산"],
        }
    )
    counts = r.count_by_field(df)
    assert counts["dining_cafe"] == 2  # 중복 제거 후 음식 2
    assert counts["grocery"] == 1
    assert "leisure" not in counts

    facts = r.to_facts({"dining_cafe": 45, "grocery": 3, "leisure": 0})
    assert "밀집" in facts["dining_cafe"][0][0]  # 45 >= 30 → 밀집
    assert facts["grocery"][1] == 3
    assert "leisure" not in facts  # 0이면 생략


def test_missing_column_returns_empty(caplog):
    pd = pytest.importorskip("pandas")
    r = _refresh()
    df = pd.DataFrame({"bizesId": ["1"], "wrongCol": ["음식"]})  # indsLclsNm 없음
    assert r.count_by_field(df) == {}  # 추측 안 하고 빈 집계 + 로그


def test_region_facts_db_roundtrip(tmp_path):
    db = str(tmp_path / "t.db")
    trades_store.write_region_facts("mapo-m", "dining_cafe", ["음식점·카페 45곳 밀집"], 45, "src", db_path=db)
    got = trades_store.read_region_facts("mapo-m", db_path=db)
    assert got["dining_cafe"] == ["음식점·카페 45곳 밀집"]
    # 멱등(덮어쓰기)
    trades_store.write_region_facts("mapo-m", "dining_cafe", ["음식점·카페 50곳 밀집"], 50, "src", db_path=db)
    assert trades_store.read_region_facts("mapo-m", db_path=db)["dining_cafe"] == ["음식점·카페 50곳 밀집"]
    assert trades_store.read_region_facts("없는지역", db_path=db) == {}


def test_narrator_merges_db_and_yaml(tmp_path, monkeypatch):
    """DB(자동 상권) + YAML(수기 transport) 병합. DB가 grocery/dining을 덮는다."""
    from app.agents import narrator

    db = str(tmp_path / "t.db")
    trades_store.write_region_facts("mapo-m", "dining_cafe", ["음식점·카페 99곳 밀집"], 99, "src", db_path=db)
    monkeypatch.setenv("TRADES_DB", db)
    f = narrator._facts_for("mapo-m")
    assert f["dining_cafe"] == ["음식점·카페 99곳 밀집"]  # DB가 YAML 예시를 덮음
    assert "transport" in f  # YAML 수기 transport 유지


def test_sample_trade_picks_median(tmp_path):
    db = str(tmp_path / "t.db")
    conn = trades_store.connect(db)
    conn.executemany(
        "INSERT INTO trades (sigungu_code, umd_name, trade_type, price, monthly, area_m2, deal_ym, collected_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        [
            ("11", "망원동", "sale", 400_000_000, 0, 40.0, "202605", "x"),
            ("11", "망원동", "sale", 500_000_000, 0, 50.0, "202606", "x"),
            ("11", "망원동", "sale", 900_000_000, 0, 80.0, "202606", "x"),
        ],
    )
    conn.commit()
    conn.close()
    t = trades_store.sample_trade("망원동", "sale", db_path=db)
    assert t["price"] == 500_000_000 and t["area_m2"] == 50.0  # 중위(400·500·900)=500
    assert t["overBudget"] is False
    assert trades_store.sample_trade("없는동", "sale", db_path=db) is None
    # G2: 예산 상한 이하에서 선정 — 4.5억 캡이면 5억·9억 제외 → 400만 남아 400 선정
    capped = trades_store.sample_trade("망원동", "sale", max_price=450_000_000, db_path=db)
    assert capped["price"] == 400_000_000 and capped["overBudget"] is False
    # 상한 이하 표본이 없으면 초과 사례를 쓰되 overBudget=True로 표기(폴백)
    over = trades_store.sample_trade("망원동", "sale", max_price=300_000_000, db_path=db)
    assert over["overBudget"] is True


def test_trade_fact_formats(tmp_path, monkeypatch):
    from app.agents import narrator

    db = str(tmp_path / "t.db")
    conn = trades_store.connect(db)
    conn.execute(
        "INSERT INTO trades (sigungu_code, umd_name, trade_type, price, monthly, area_m2, deal_ym, collected_at) "
        "VALUES ('11','망원동','jeonse',280000000,0,32.0,'202605','x')"
    )
    conn.commit()
    conn.close()
    monkeypatch.setenv("TRADES_DB", db)
    fact = narrator._trade_fact("마포구 망원동", "이사")
    assert "실거래" in fact and "2.8억" in fact and "전세" in fact
    assert narrator._trade_fact("없는구 없는동", "매매") == ""  # 데이터 없으면 빈 문자열


def test_transit_fallback_estimate(monkeypatch):
    from app.core.config import settings
    from app.tools import transit

    monkeypatch.setattr(settings, "odsay_api_key", "")  # 키 없음 → 예상치
    c = transit.commute(37.5561, 126.9026, 37.3948, 127.1112)  # 망원동→판교
    assert c["estimated"] is True and c["minutes"] > 12 and c["transfers"] is None


def test_transit_fact_in_narrator():
    from app.agents import narrator

    reg = {"id": "mapo-m", "name": "마포구 망원동", "lat": 37.5561, "lng": 126.9026}
    f = narrator._transit_fact(reg, "1인")  # 1인 → 판교
    assert "판교" in f and "분" in f
    assert narrator._transit_fact({"name": "좌표없음"}, "1인") == ""  # 좌표 없으면 빈 문자열


def test_region_transit_roundtrip(tmp_path):
    db = str(tmp_path / "t.db")
    trades_store.write_region_transit("seongbuk", "여의도(금융권)", 46, 1, False, db_path=db)
    got = trades_store.read_region_transit("seongbuk", "여의도(금융권)", db_path=db)
    assert got == {"minutes": 46, "transfers": 1, "estimated": False}
    assert trades_store.read_region_transit("seongbuk", "없는직장", db_path=db) is None


def test_narrator_transit_prefers_cache(tmp_path, monkeypatch):
    from app.agents import narrator

    db = str(tmp_path / "t.db")
    trades_store.write_region_transit("seongbuk", "여의도(금융권)", 46, 1, False, db_path=db)
    monkeypatch.setenv("TRADES_DB", db)
    reg = {"id": "seongbuk", "name": "성북구 길음동", "lat": 37.6038, "lng": 127.0193}
    f = narrator._transit_fact(reg, "신혼")  # 신혼 → 여의도, 캐시 실측
    assert "여의도" in f and "46분" in f and "환승 1회" in f and "예상" not in f


def test_preferred_area_to_sigungu():
    from app.routers.api import _sigungu_code

    assert _sigungu_code("마포구") == "11440"
    assert _sigungu_code("노원구") == "11350"
    assert _sigungu_code("") is None  # 상관없음 → 전체
    assert _sigungu_code("없는구") is None
