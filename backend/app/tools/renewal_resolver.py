"""갱신 상황 결정론 resolver — LLM 없음.

renewal_cases.yaml(결정표)만 읽어 확정 상황들을 조합한다. if-else 트리가 아니라
선언적 결정표 순회. guidance/citation은 yaml 원문 그대로 반환(재작성·조립 금지).

핵심 규약:
- requires 교차검증: 구조화 사실과 불일치하면 그 케이스 '기각'(rejected). 자유입력만으로
  계산이 바뀌지 않는다(예: notice_deadline_passed 인데 noticeDaysLeft>=0 → 기각).
- cap_pct 충돌: priority 내림차순 '승자독식'(최우선 케이스 하나만). 나머지 effect는 누적.
- 승인 0건 → simple_increase 기본(cap 5) = 현행 동작.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from ..core.rules import read_yaml

log = logging.getLogger("renewal_resolver")

_DEFAULT_CAP_PCT = 5  # simple_increase 기본(결정표 밖 폴백과 동일 값) — 골든패스 불변 보장


_BRANCH_KEYS = ("renewal", "move", "purchase")


@dataclass
class RenewalResolution:
    cap_pct: Optional[int]  # 적용 상한 %. None = 상한 미적용(권 소진)
    effects: dict = field(default_factory=dict)  # {"warn": bool, "apply_conversion_cap": bool}
    guidances: list[str] = field(default_factory=list)  # yaml 원문 그대로
    citations: list[str] = field(default_factory=list)
    applied: list[str] = field(default_factory=list)  # 적용된 case id(priority 순)
    rejected: list[dict] = field(default_factory=list)  # [{"id":..., "reason":...}]
    # 상황 → 3갈래 힌트(표시 계층). key=renewal|move|purchase, applied 케이스만. 계산 무관.
    branchHints: dict = field(default_factory=lambda: {k: [] for k in _BRANCH_KEYS})


@lru_cache(maxsize=1)
def _cases() -> dict[str, dict]:
    """id → case. 로드 1회 캐시. checked_at 없으면 경고(법령 검증 신호)."""
    doc = read_yaml("renewal_cases.yaml")
    out: dict[str, dict] = {}
    for c in doc.get("cases", []):
        cid = c.get("id")
        if not cid:
            continue
        if c.get("checked_at") in (None, "", "null"):
            log.warning("갱신 결정표 미검증: %s (checked_at 없음 — 법령 검증 필요)", cid)
        out[cid] = c
    return out


def _requires_ok(requires: dict, facts: dict) -> tuple[bool, str]:
    """requires 각 조건을 facts(구조화 사실)로 검증. 실패 시 (False, 사유)."""
    for key, cond in (requires or {}).items():
        actual = facts.get(key)
        if actual is None:
            return False, f"{key} 알 수 없음"
        # cond 형식: "<연산자> <숫자>" (예 "< 0"). 지원: < <= > >= == !=
        parts = str(cond).split()
        if len(parts) != 2:
            return False, f"{key} 조건 형식 오류({cond})"
        op, rhs = parts[0], float(parts[1])
        ok = {
            "<": actual < rhs,
            "<=": actual <= rhs,
            ">": actual > rhs,
            ">=": actual >= rhs,
            "==": actual == rhs,
            "!=": actual != rhs,
        }.get(op)
        if ok is None:
            return False, f"{key} 연산자 미지원({op})"
        if not ok:
            return False, f"{key}={actual} 이 조건 '{cond}' 불충족"
    return True, ""


def resolve(situations: list[str], contract, days_left: int) -> RenewalResolution:
    """확정 갱신 상황 목록 → 결정론 조합. days_left = noticeDaysLeft(compare가 계산해 넘김)."""
    cases = _cases()
    facts = {"noticeDaysLeft": days_left}

    survivors: list[dict] = []
    rejected: list[dict] = []
    seen: set[str] = set()
    for sid in situations:
        sid = str(sid)
        if sid in seen:
            continue
        seen.add(sid)
        case = cases.get(sid)
        if case is None:
            # unknown 등 결정표 밖 → 계산 미반영(consultNote 경로). 기각으로 기록.
            rejected.append({"id": sid, "reason": "결정표에 없는 상황(계산 미반영)"})
            continue
        ok, reason = _requires_ok(case.get("requires") or {}, facts)
        if not ok:
            rejected.append({"id": sid, "reason": reason})
            continue
        survivors.append(case)

    survivors.sort(key=lambda c: c.get("priority", 0), reverse=True)

    # cap_pct: priority 순 첫 'cap_pct 보유' 케이스가 승자독식(0·null 모두 명시값). 없으면 기본 5.
    cap_pct: Optional[int] = _DEFAULT_CAP_PCT
    for c in survivors:
        eff = c.get("effect") or {}
        if "cap_pct" in eff:
            cap_pct = eff["cap_pct"]  # 0 또는 None 포함
            break

    # 나머지 effect 누적(warn, apply_conversion_cap)
    effects: dict = {}
    for c in survivors:
        eff = c.get("effect") or {}
        if eff.get("warn"):
            effects["warn"] = True
        if eff.get("apply_conversion_cap"):
            effects["apply_conversion_cap"] = True

    # 3갈래 힌트 — applied(survivors)만, 여러 상황이 같은 갈래면 누적. 문구는 yaml 원문 그대로.
    branch_hints: dict = {k: [] for k in _BRANCH_KEYS}
    for c in survivors:
        bh = c.get("branch_hint")
        if not bh:
            continue
        for key in _BRANCH_KEYS:
            h = bh.get(key)
            if h:  # null 아닌 것만
                branch_hints[key].append({"situationId": c["id"], "tone": h["tone"], "text": h["text"]})

    return RenewalResolution(
        cap_pct=cap_pct,
        effects=effects,
        guidances=[c["guidance"] for c in survivors],
        citations=[c["citation"] for c in survivors],
        applied=[c["id"] for c in survivors],
        rejected=rejected,
        branchHints=branch_hints,
    )
