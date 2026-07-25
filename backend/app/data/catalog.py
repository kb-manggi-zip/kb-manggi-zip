"""상품/씬 폴백 데이터 — 프론트 src/data/products.ts · scenes.ts 이식.

Phase B4에서 agents/matcher(RAG) · agents/narrator(LLM)가 이 shape을 채운다.
"""

from ..schemas import Product, ProductsResponse

# ── 갈래별 상품 (products.ts) ───────────────────────────────────────
PRODUCTS_RENEWAL = ProductsResponse(
    branch="갱신",
    mainLoan=Product(
        name="KB 전세대출 연장·증액",
        condition="증액분 LTV 80% 이내, 소득 심사",
        recommendReason="기존 대출 조건 유지로 추가 심사 최소화",
        maxAmount=200_000_000,
        basis="은행·보증기관 공시 기준",
    ),
    guarantee=Product(
        name="전세보증금 반환보증 갱신 점검",
        condition="갱신 계약서 작성 후 재신청",
        recommendReason="갱신 후에도 보증 공백 없이 이어가요",
        basis="보증기관 공시 기준",
    ),
)

PRODUCTS_MOVE = ProductsResponse(
    branch="이사",
    mainLoan=Product(
        name="KB 청년·신혼 전세대출",
        condition="부부합산 연소득 7천만원 이하, LTV 80%",
        recommendReason="우대금리 적용 대상 여부 확인해보세요",
        maxAmount=300_000_000,
        basis="은행·보증기관 공시 기준",
    ),
    guarantee=Product(
        name="전세보증금 반환보증",
        condition="새 계약 체결 후 1개월 이내 신청",
        recommendReason="새 집 계약 시 함께 확인하면 절차가 간편해요",
        basis="보증기관 공시 기준",
    ),
)

PRODUCTS_BUY = ProductsResponse(
    branch="매매",
    mainLoan=Product(
        name="KB 디딤돌·주택담보대출",
        condition="생애최초 LTV 80%, DSR 40% 이내",
        recommendReason="신혼 우대금리 대상인지 확인해보세요",
        maxAmount=500_000_000,
        basis="은행·보증기관 공시 기준",
    ),
    guarantee=Product(
        name="화재보험",
        condition="매매 계약 체결 후 바로 가입",
        recommendReason="대출 실행 전 필수 — 은행 요청 서류",
        basis="보험사 공시 기준",
    ),
    extra=Product(
        name="주택청약종합저축 유지",
        condition="월 2~50만원 납입",
        recommendReason="매매 후에도 청약통장은 계속 유지하세요",
        basis="국토교통부 기준",
    ),
)


def products_for(branch: str) -> ProductsResponse:
    return {"갱신": PRODUCTS_RENEWAL, "이사": PRODUCTS_MOVE, "매매": PRODUCTS_BUY}.get(branch, PRODUCTS_BUY)
