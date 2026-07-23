"""KB부동산 데이터허브 — 평균가·전세가율 (Phase B2, Optional).

실패해도 서비스는 진행한다 (Optional 필드). KB 데이터는 어필 포인트.
STUB: 지금은 None 반환. B2에서 채우면 Region/비교표에 병기.
"""

from ..core.cache import cached


@cached()
def avg_price(region_name: str) -> dict | None:
    """동네 평균 매매/전세가·전세가율. 실패 시 None."""
    # STUB: Phase B2 — KB 데이터허브 조회
    return None
