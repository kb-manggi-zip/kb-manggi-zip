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
