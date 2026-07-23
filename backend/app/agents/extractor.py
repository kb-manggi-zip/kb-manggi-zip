"""계약서 Vision 추출 — Phase B5 SEAM (미구현).

이미지 1장(계약서 사진) → 원샷 추출 {deposit, monthlyRent, expiryDate, confidence}.
낮은 confidence 필드는 null + "확인 불가"로 둔다 (지어내지 않는다).

구현 위치:
  - core/llm.py 에 Vision 호출 추가 (Claude messages + image block)
  - 아래 extract_contract 채우고, routers/api.py 에 POST /api/extract-contract 활성화
  - 프론트 "사진으로 채우기" 버튼은 이 Phase 완료 후 활성화 (기획서 B5)
"""

from typing import Optional, TypedDict


class ExtractResult(TypedDict):
    deposit: Optional[int]
    monthlyRent: Optional[int]
    expiryDate: Optional[str]
    confidence: float


def extract_contract(image_bytes: bytes) -> ExtractResult:  # pragma: no cover
    # STUB: Phase B5 — Claude Vision 연동. 낮은 confidence는 null 처리.
    raise NotImplementedError("계약서 Vision 추출은 Phase B5에서 구현합니다. 현재는 직접 입력(SC-02)만 지원.")
