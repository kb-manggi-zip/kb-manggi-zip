"""상품/씬 폴백 데이터 — 프론트 src/data/products.ts · scenes.ts 이식.

Phase B4에서 agents/matcher(RAG) · agents/narrator(LLM)가 이 shape을 채운다.
"""

from ..schemas import Product, ProductsResponse, Scene

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


# ── 하루 시뮬레이션 씬 (scenes.ts) ──────────────────────────────────
_U = "https://images.unsplash.com/"

SCENES_MOVE: list[Scene] = [
    Scene(
        time="🌅 07:40",
        emoji="🚶",
        visual=f"{_U}photo-1555883006-0f5a0915a80f?w=390&h=500&fit=crop&auto=format",
        caption1="역까지 도보 8분, 완만한 내리막",
        caption2="상계역 4호선 직통, 시청까지 32분",
        basis="실거래·경로 데이터 기준",
    ),
    Scene(
        time="🌤 09:00",
        emoji="☕",
        visual=f"{_U}photo-1501339847302-ac426a4a7cbb?w=390&h=500&fit=crop&auto=format",
        caption1="단지 앞 편의점 겸 카페",
        caption2="아메리카노 2,500원, 매일 들리는 거리",
        basis="네이버지도 기준",
    ),
    Scene(
        time="☀️ 12:30",
        emoji="🍱",
        visual=f"{_U}photo-1555396273-367ea4eb4db5?w=390&h=500&fit=crop&auto=format",
        caption1="반경 300m 식당 16곳",
        caption2="점심 평균 9,800원대",
        basis="카카오맵 기준",
    ),
    Scene(
        time="🌇 18:30",
        emoji="🛒",
        visual=f"{_U}photo-1578916171728-46686eac8d58?w=390&h=500&fit=crop&auto=format",
        caption1="도보 5분 대형마트",
        caption2="주차 무료, 주말 혼잡",
        basis="로드뷰 기준",
    ),
    Scene(
        time="🌙 22:00",
        emoji="🏠",
        visual=f"{_U}photo-1502672260266-1c1ef2d93688?w=390&h=500&fit=crop&auto=format",
        caption1="방 2개, 남향, 관리비 9만원",
        caption2="조용한 주택가, 밤 소음 적음",
        basis="실거래 기준",
    ),
]

SCENES_BUY: list[Scene] = [
    Scene(
        time="🌅 07:20",
        emoji="🚇",
        visual=f"{_U}photo-1556075798-4825dfaaf498?w=390&h=500&fit=crop&auto=format",
        caption1="합정역 2·6호선 환승, 도보 4분",
        caption2="출근 피크타임 35분 여유",
        basis="경로 데이터 기준",
    ),
    Scene(
        time="☕ 08:30",
        emoji="🏙",
        visual=f"{_U}photo-1545093149-618ce3bcf49d?w=390&h=500&fit=crop&auto=format",
        caption1="홍대·합정 카페 벨트 도보권",
        caption2="매달 1곳씩 새 카페 오픈 중",
        basis="네이버플레이스 기준",
    ),
    Scene(
        time="🌤 13:00",
        emoji="🌿",
        visual=f"{_U}photo-1476514525535-07fb3b4ae5f1?w=390&h=500&fit=crop&auto=format",
        caption1="한강공원 도보 10분",
        caption2="주말 피크닉 명소",
        basis="로드뷰 기준",
    ),
    Scene(
        time="🌆 19:00",
        emoji="🍽",
        visual=f"{_U}photo-1414235077428-338989a2e8c0?w=390&h=500&fit=crop&auto=format",
        caption1="합정 먹자골목, 저녁 다양",
        caption2="1인 평균 18,000원대",
        basis="카카오맵 기준",
    ),
    Scene(
        time="🌙 22:30",
        emoji="🏡",
        visual=f"{_U}photo-1560448204-e02f11c3d0e2?w=390&h=500&fit=crop&auto=format",
        caption1="방 2개 25평형, 남향 채광 우수",
        caption2="내 집이 된 첫날 밤",
        basis="실거래 기준",
    ),
]


def scenes_for(branch: str) -> tuple[list[Scene], int]:
    """(scenes, monthlyCost) — client.ts simulate 폴백과 동일."""
    if branch == "매매":
        return SCENES_BUY, 1_400_000
    return SCENES_MOVE, 900_000
