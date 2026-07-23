"""지역 판정 — 규제지역/수도권 (B1.5 리서치 반영, 순수).

모든 매매 계산의 선행. rules/regions.yaml 사용.
스펙 pseudocode 보완: 데모 동네("마포구 합정동")는 "서울" 문자열이 없으므로
seoul_gu(25 자치구) 목록으로도 서울=규제를 판정한다.
"""

from ..core.rules import read_yaml


def classify_region(region_name: str, reg_rules: dict | None = None) -> dict:
    """동/구/시 문자열 → {is_metro, is_regulated}."""
    reg_rules = reg_rules if reg_rules is not None else read_yaml("regions.yaml")

    regulated = reg_rules.get("regulated", {})
    seoul_gu = reg_rules.get("seoul_gu", [])
    gyeonggi = regulated.get("gyeonggi", [])
    metro = reg_rules.get("metro", [])

    is_seoul = ("서울" in region_name) or any(gu in region_name for gu in seoul_gu)
    is_regulated = (bool(regulated.get("seoul_all")) and is_seoul) or any(g in region_name for g in gyeonggi)
    is_metro = is_seoul or any(m in region_name for m in metro)

    return {"is_metro": bool(is_metro), "is_regulated": bool(is_regulated)}
