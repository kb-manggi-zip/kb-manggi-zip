"""상품 매칭 에이전트 — 갈래별 KB 상품 + 사유 (LLM/RAG seam).

지금: catalog fixture 반환 → /api/products 동작.
Phase B4: data/kb_products/*.md → FAISS → top3 + 사유(숫자는 문서 원문만 인용).
가드레일: 상품 '추천/가입하세요' 금지 — 조건·사유 서술만.
"""

from ..data.catalog import products_for
from ..schemas import Branch, CompareResponse, ProductsResponse


def run(branch: Branch, comparison: CompareResponse | None = None) -> ProductsResponse:
    # STUB: RAG 매칭 + LLM 사유(Phase B4). 현재는 결정론적 fixture.
    return products_for(branch)
