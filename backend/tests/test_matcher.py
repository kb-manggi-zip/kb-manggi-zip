"""상품 매칭 — 문서(RAG 소스) 기반, 갈래별 슬롯, 숫자 비할루시네이션(폴백=문서 원문)."""

from app.agents import matcher


def test_load_products_has_docs():
    p = matcher.load_products()
    # 상품 5종 + 보장 2종
    for pid in [
        "kb_mortgage",
        "kb_jeonse",
        "didimdol",
        "buttimok_youth",
        "kb_chungyak_loan",
        "return_guarantee",
        "fire_insurance",
    ]:
        assert pid in p, pid
        assert p[pid]["source_url"]  # 출처 필수


def test_buy_package():
    r = matcher.run("매매")
    assert r.branch == "매매"
    assert r.mainLoan.name == "KB 주택담보대출"
    assert r.guarantee and r.guarantee.name == "화재보험"
    assert r.extra and r.extra.name == "주택청약종합저축"


def test_renew_and_move_use_jeonse():
    for br in ["갱신", "이사"]:
        r = matcher.run(br)
        assert r.mainLoan.name == "KB 전세자금대출"
        assert r.mainLoan.maxAmount == 222_000_000  # 문서 값 그대로
        assert r.guarantee and "반환보증" in r.guarantee.name


def test_move_monthly_uses_wolse_loan():
    # 갱신·이사(월세)는 전세대출(보증금 담보 상품)이 안 맞아서 별도 상품으로 분기(2026-07-30).
    for br in ["갱신", "이사"]:
        r = matcher.run(br, contract_type="월세")
        assert r.mainLoan.name == "주거안정 월세대출"
        assert r.guarantee is None  # 전세보증금 반환보증은 월세 계약엔 전제가 안 맞아 제외
        # 전세(기본값)는 기존 그대로 전세대출 유지
        r_jeonse = matcher.run(br, contract_type="전세")
        assert r_jeonse.mainLoan.name == "KB 전세자금대출"


def test_reason_is_grounded_fallback():
    # LLM 비활성 → recommendReason == 문서의 reason (지어내기 없음)
    r = matcher.run("매매")
    doc = matcher.load_products()["kb_mortgage"]
    assert r.mainLoan.recommendReason == doc["reason"]
