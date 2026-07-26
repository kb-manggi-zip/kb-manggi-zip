"""규칙(YAML) 로더.

- 모든 규정 수치는 rules/*.yaml에서만 온다 (하드코딩 금지).
- 각 항목은 {value, source_url, checked_at, note} 구조.
- checked_at 이 null 이면 경고 로그 (제출 전 법령 검증 필요 신호).
- 로드 결과는 프론트 engine/rules.ts 와 동일한 camelCase 네임스페이스로 노출
  → tools/compare.py 가 참조 구현(compare.ts)과 1:1로 읽히도록.
"""

import logging
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel

from .config import settings

log = logging.getLogger("kb.rules")


class RenewalRules(BaseModel):
    increaseCap: float
    conversionRate: float


class OneTimeRules(BaseModel):
    moveBase: float
    moveBaseBuy: float


class Rules(BaseModel):
    renewal: RenewalRules
    oneTime: OneTimeRules
    noticeDeadlineMonths: int
    # 주: 대출/보증 규제값(LTV·DSR·전세금리·보증료)은 lending_regulated.yaml·
    #     guarantee_hug.yaml(검증본)에서 read_yaml로 직접 로드한다. 구 lending.yaml·
    #     guarantee.yaml은 미사용이라 제거됨(무의미한 미검증 경고 방지).


def _load_yaml(name: str) -> dict:
    path = Path(settings.rules_dir) / name
    if not path.exists():
        raise FileNotFoundError(f"규칙 파일 없음: {path}")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache
def read_yaml(name: str) -> dict:
    """구조화된 규칙 파일(테이블형)을 원 dict로 로드.

    regions.yaml · policy_loans.yaml · lending_regulated.yaml · guarantee_hug.yaml 처럼
    {value, source_url, checked_at} 리프 구조가 아닌 파일용 (B1.5 리서치 반영분).
    """
    return _load_yaml(name)


def _value(doc: dict, key: str, file: str) -> float:
    entry = doc.get(key)
    if entry is None or "value" not in entry:
        raise KeyError(f"{file}:{key} 에 value 없음")
    if entry.get("checked_at") in (None, "", "null"):
        log.warning("규칙 미검증: %s:%s (checked_at 없음 — 법령 검증 필요)", file, key)
    return entry["value"]


@lru_cache
def get_rules() -> Rules:
    renewal = _load_yaml("renewal.yaml")
    one_time = _load_yaml("one_time.yaml")

    return Rules(
        renewal=RenewalRules(
            increaseCap=_value(renewal, "increase_cap", "renewal.yaml"),
            conversionRate=_value(renewal, "conversion_rate", "renewal.yaml"),
        ),
        oneTime=OneTimeRules(
            moveBase=_value(one_time, "move_base", "one_time.yaml"),
            moveBaseBuy=_value(one_time, "move_base_buy", "one_time.yaml"),
        ),
        noticeDeadlineMonths=int(_value(renewal, "notice_deadline_months", "renewal.yaml")),
    )
