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


def test_region_with_real_tags_differs_from_generic_fallback():
    """실제 상권 태그가 있는 동(mapo-m=망원동, region_enrich.yaml에 id로 매칭됨)은 태그 데이터가
    아예 없는 동(seongbuk-m)과 다른 하루가 나온다(2026-08-02: 수기 오버라이드였던 예전 테스트를
    실측 태그 기반 동적 조립 검증으로 교체 — regions.yaml의 지역별 오버라이드는 고정 3씬 설계와
    맞지 않는 구식 5씬 스톡사진이라 제거됨)."""
    with_tags = narrator.run("이사", "mapo-m")
    without_tags = narrator.run("이사", "seongbuk-m")
    assert _captions(with_tags) != _captions(without_tags)
    assert any("상권 실측" in s.basis for s in with_tags.scenes)
    assert all(s.basis == "" for s in without_tags.scenes)  # 근거 없음 → 칩 자체를 숨기는 빈 문자열


def test_wolse_vs_jeonse_distinct():
    """'월세로'(mapo-m)와 '전세로'(seongbuk)가 서로 다른 하루여야 한다(사용자 리포트)."""
    wolse = narrator.run("이사", "mapo-m")
    jeonse = narrator.run("이사", "seongbuk")
    assert _captions(wolse) != _captions(jeonse)


def test_unknown_region_gets_generic_three_scenes():
    """모르는 region_id도 3씬은 보장한다(2026-08-02 재설계) — 예전엔 태그 없으면 구식 5씬 base로
    빠졌지만, region_id 자체가 없는 경우(동 선택 전)만 base로 폴백하고 나머진 제네릭 3씬."""
    known = narrator.run("이사", "does-not-exist")
    assert len(known.scenes) == 3
    assert all(s.basis == "" for s in known.scenes)  # 근거 없음 → 칩 자체를 숨기는 빈 문자열


def test_no_region_id_falls_back_to_base():
    """region_id 자체가 없을 때만(동 선택 전) 구식 5씬 base로 폴백한다."""
    base = narrator.run("이사", "")
    assert len(base.scenes) == 5


# ── 개인화 라이프스타일 내레이션 ('온라인 발품') ──────────────────────────
from app.agents import briefing as _briefing  # noqa: E402
from app.schemas import BriefingRequest  # noqa: E402


def test_profile_selection_differs():
    """가구 유형별 소비 프로필이 다르게 선택된다."""
    assert narrator.profile_for("신혼")["traits"] != narrator.profile_for("1인")["traits"]
    assert narrator.profile_for(None) == narrator.profile_for("존재안함")  # 둘 다 default


def test_lifestyle_prompt_grounds_on_region_and_profile():
    """프롬프트에 동네 실데이터(이름·태그) + 소비 성향이 그라운딩된다."""
    ctx = {
        "region": {"name": "마포구 망원동", "tags": ["한강공원", "힙한거리"]},
        "finance": {"household": "1인"},
        "branch": "이사",
    }
    system, user = narrator.build_lifestyle_prompt(ctx)
    assert "망원동" in user and "한강공원" in user
    assert "카페" in user or "배달" in user  # 1인가구 성향 반영
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


def test_region_facts_block_injects_when_present():
    """region_facts.yaml에 있는 regionId → 대표 정보 블록이 생성된다(예시 mapo-m)."""
    block = narrator._facts_block("mapo-m")
    assert "동네 대표 정보" in block and "망원역" in block
    assert narrator._facts_block("존재안함") == ""  # 없으면 빈 문자열


def test_lifestyle_prompt_uses_region_facts():
    """region.id가 facts에 있으면 프롬프트에 대표 정보가 들어간다."""
    ctx = {
        "region": {"id": "mapo-m", "name": "마포구 망원동", "tags": []},
        "finance": {"household": "1인"},
        "branch": "이사",
    }
    _, user = narrator.build_lifestyle_prompt(ctx)
    assert "교통" in user and "망원역" in user
