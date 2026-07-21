"""★ Phase B1 핵심 DoD — 프론트 engine 과 백엔드 compare 의 전 필드 동치.

fixtures/compare_cases.json 은 프론트 compare.ts 출력(오차 0 기준).
생성: cd backend && TZ=UTC npx tsx scripts/gen_fixtures.mjs
"""
import json
from datetime import datetime
from pathlib import Path

import pytest

from app.schemas import ContractInfo, FinanceInfo
from app.tools.compare import compute_compare

FIXTURE = Path(__file__).parent / "fixtures" / "compare_cases.json"


def _load():
    if not FIXTURE.exists():
        pytest.skip(
            "compare_cases.json 없음 — 먼저 'TZ=UTC npx tsx scripts/gen_fixtures.mjs' 실행"
        )
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _parse_now(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


DATA = _load()
CASES = [(c["name"], c) for c in DATA["cases"]]
NOW = _parse_now(DATA["now"])


@pytest.mark.parametrize("name,case", CASES, ids=[n for n, _ in CASES])
def test_compare_matches_frontend(name, case):
    contract = ContractInfo(**case["contract"])
    finance = FinanceInfo(**case["finance"])

    got = compute_compare(contract, finance, now=NOW)
    # exclude_none: 프론트 JSON은 undefined(uncertainty)를 생략 → 동일하게 맞춤
    got_json = got.model_dump(exclude_none=True)

    assert got_json == case["expected"], f"{name} 불일치"
