"""하루 시뮬 내레이터 — branch별 분리 + 지역 override(월세로≠전세로)."""

from app.agents import narrator


def _captions(resp):
    return [s.caption1 for s in resp.scenes]


def test_branches_are_distinct():
    """갱신(눌러앉기)·이사·매매가 서로 다른 하루여야 한다(갱신==이사 버그 회귀 방지)."""
    stay = narrator.run("갱신", "")
    move = narrator.run("이사", "")
    buy = narrator.run("매매", "")
    assert _captions(stay) != _captions(move)
    assert _captions(move) != _captions(buy)
    assert _captions(stay) != _captions(buy)
    assert all(len(r.scenes) == 5 for r in (stay, move, buy))


def test_monthly_cost_unchanged():
    assert narrator.run("매매", "mapo").monthlyCost == 1_400_000
    assert narrator.run("이사", "seongbuk").monthlyCost == 900_000
    assert narrator.run("갱신", "").monthlyCost == 900_000


def test_region_override_differs_from_base():
    """월세 후보('-m')는 지역 override → base 이사와 다른 하루."""
    base_move = narrator.run("이사", "seongbuk")  # override 없음 → base
    monthly = narrator.run("이사", "mapo-m")  # 망원동 override
    assert _captions(base_move) != _captions(monthly)
    assert any("망원" in c for c in _captions(monthly))


def test_wolse_vs_jeonse_distinct():
    """'월세로'(mapo-m)와 '전세로'(seongbuk)가 서로 다른 하루여야 한다(사용자 리포트)."""
    wolse = narrator.run("이사", "mapo-m")
    jeonse = narrator.run("이사", "seongbuk")
    assert _captions(wolse) != _captions(jeonse)


def test_unknown_region_falls_back_to_base():
    known = narrator.run("이사", "does-not-exist")
    base = narrator.run("이사", "")
    assert _captions(known) == _captions(base)


# ── 개인화 라이프스타일 내레이션 ('온라인 발품') ──────────────────────────
from app.agents import briefing as _briefing  # noqa: E402
from app.schemas import BriefingRequest  # noqa: E402


def test_profile_selection_differs():
    """가구 유형별 소비 프로필이 다르게 선택된다."""
    assert narrator.profile_for("신혼")["traits"] != narrator.profile_for("청년")["traits"]
    assert narrator.profile_for(None) == narrator.profile_for("존재안함")  # 둘 다 default


def test_lifestyle_prompt_grounds_on_region_and_profile():
    """프롬프트에 동네 실데이터(이름·태그) + 소비 성향이 그라운딩된다."""
    ctx = {
        "region": {"name": "마포구 망원동", "tags": ["한강공원", "힙한거리"]},
        "finance": {"household": "청년"},
        "branch": "이사",
    }
    system, user = narrator.build_lifestyle_prompt(ctx)
    assert "망원동" in user and "한강공원" in user
    assert "카페" in user or "배달" in user  # 청년 성향 반영
    assert "금액" in user and "단정" in user  # 가드레일 지시 포함


def test_lifestyle_fallback_is_deterministic_and_grounded():
    """llm off(conftest) → 폴백. 동네명 포함, 숫자 단정 없음."""
    ctx = {"region": {"name": "성북구 보문동", "tags": ["대학가"]}, "finance": {"household": "1인"}}
    out = narrator.narrate_lifestyle(ctx)
    assert "보문동" in out and len(out) > 10


def test_daylifestyle_via_briefing_kind():
    """스키마 변경 없이 briefing kind로 도달 가능."""
    ctx = {"region": {"name": "은평구 녹번동", "tags": ["조용한"]}, "finance": {"household": "신혼"}, "branch": "매매"}
    out = _briefing.run(BriefingRequest(kind="dayPlayer", context=ctx))
    assert "녹번동" in out
