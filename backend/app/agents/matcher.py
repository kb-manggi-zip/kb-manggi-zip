"""상품 매칭 에이전트 — 갈래별 KB 상품 패키지 + 사유 (RAG 소스 + LLM seam).

설계(기획서/명세 PART 3): **매칭은 규칙(코드)**, LLM은 "왜 맞는지 사유"만.
- 상품 원문 = data/kb_products/*.md (프론트매터=구조화 필드, 본문=원문 요약, source_url).
- 갈래 → role 슬롯(mainLoan/guarantee/extra)로 상품 선택 (자격 필터의 결과).
- 숫자·요율은 문서 원문만 인용(지어내기 금지). 권유 표현 금지(가드레일).

※ FAISS/벡터검색은 상품이 소수(구조화)라 과함 — 태그(branch) 기반 검색으로 충분.
  상품이 수십 개로 늘거나 자연어 질의가 필요해지면 core에 임베딩+FAISS 계층 추가.
"""

import re
from functools import lru_cache

import yaml

from ..core.config import BACKEND_ROOT
from ..core.llm import generate
from ..schemas import Branch, CompareResponse, ContractType, Product, ProductsResponse

PRODUCTS_DIR = BACKEND_ROOT / "data" / "kb_products"

# 갈래 → 슬롯(product_id). 자격 필터 결과를 이 매핑으로 표현.
# 갱신·이사(월세)는 보증금 담보 상품인 전세대출이 안 맞아서 별도 슬롯(_BRANCH_SLOTS_MONTHLY)으로 분기.
_BRANCH_SLOTS: dict[str, dict[str, str]] = {
    "갱신": {"mainLoan": "kb_jeonse", "guarantee": "return_guarantee", "extra": "buttimok_youth"},
    "이사": {"mainLoan": "kb_jeonse", "guarantee": "return_guarantee", "extra": "buttimok_youth"},
    "매매": {"mainLoan": "kb_mortgage", "guarantee": "fire_insurance", "extra": "kb_chungyak_loan"},
}
_BRANCH_SLOTS_MONTHLY: dict[str, str] = {
    "mainLoan": "wolse_loan"
}  # 버팀목·반환보증은 전세 보증금 전제라 월세엔 제외(갱신·이사 공통)


@lru_cache
def load_products() -> dict[str, dict]:
    """kb_products/*.md 프론트매터 → {product_id: fields} (RAG 소스)."""
    out: dict[str, dict] = {}
    for path in sorted(PRODUCTS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
        if not m:
            continue
        meta = yaml.safe_load(m.group(1)) or {}
        meta["_body"] = m.group(2).strip()
        if "product_id" in meta:
            out[meta["product_id"]] = meta
    return out


def _reason(pd: dict, branch: str) -> str:
    """추천 사유 — LLM seam. 비활성 시 문서의 reason(결정론적). 숫자는 문서 원문만."""
    fallback_text = pd.get("reason", "조건을 확인해 보세요")
    return generate(
        system=(
            "아래 상품 문서를 근거로, 이 갈래에 왜 조건이 맞는지 1~2문장으로 서술한다. "
            "숫자·요율·상품명은 문서에 있는 것만 인용한다. 추천·가입 권유·단정 표현은 쓰지 않는다."
        ),
        user=f"갈래={branch}\n상품={pd['name']}\n조건={pd.get('condition', '')}\n문서:\n{pd.get('_body', '')}",
        fallback=lambda: fallback_text,
    )


def _to_product(pd: dict, branch: str) -> Product:
    return Product(
        name=pd["name"],
        condition=pd.get("condition", ""),
        recommendReason=_reason(pd, branch),
        maxAmount=pd.get("max_amount"),
        basis=pd.get("basis", ""),
    )


def run(
    branch: Branch,
    comparison: CompareResponse | None = None,
    contract_type: ContractType | None = None,
) -> ProductsResponse:
    """갈래별 KB '대출+보장' 패키지. 상품 문서 기반 + LLM 사유(seam).

    ※ 자격(소득·나이·무주택) 정밀 필터는 finance가 필요하나 ProductsRequest엔 없음
      → 갈래 기반 매핑까지 구현. 개인화 필터는 스키마 확장 후(사람 결정) 연결.
    contract_type: '갱신'·'이사' 갈래에서 전세/월세 구분(전세대출은 보증금 담보 상품이라 월세엔 안 맞음).
    """
    products = load_products()
    if branch in ("갱신", "이사") and contract_type == "월세":
        slots = _BRANCH_SLOTS_MONTHLY
    else:
        slots = _BRANCH_SLOTS.get(branch, _BRANCH_SLOTS["매매"])

    resp = ProductsResponse(branch=branch, mainLoan=_to_product(products[slots["mainLoan"]], branch))
    if products.get(slots.get("guarantee", "")):
        resp.guarantee = _to_product(products[slots["guarantee"]], branch)
    if products.get(slots.get("extra", "")):
        resp.extra = _to_product(products[slots["extra"]], branch)
    return resp
