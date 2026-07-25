"""개인화 브리핑 — 상황(contract·finance) → 가이드 프롬프트 반영. (LLM 없이 결정론 검증)"""

from app.agents import briefing
from app.schemas import BriefingRequest


def test_situation_monthly_youth():
    ctx = {"contract": {"type": "월세"}, "finance": {"household": "1인", "under35": True, "firstHome": "아니오"}}
    s = briefing._situation(ctx)
    assert "월세" in s
    assert "1인 가구" in s
    assert "만 35세 미만" in s
    assert "생애최초" not in s  # firstHome=아니오 → 미포함


def test_situation_newlywed_firsthome():
    ctx = {"contract": {"type": "전세"}, "finance": {"household": "신혼", "under35": False, "firstHome": "예"}}
    s = briefing._situation(ctx)
    assert "신혼 가구" in s
    assert "생애최초" in s
    assert "만 35세" not in s


def test_user_prompt_compare_embeds_situation():
    req = BriefingRequest(
        kind="compare",
        context={
            "contract": {"type": "월세"},
            "finance": {"household": "1인", "under35": True, "firstHome": "모름"},
            "name": "고객",
            "comparison": {"branches": []},
        },
    )
    p = briefing._user_prompt(req)
    assert "사용자 상황" in p and "월세" in p and "비교표" in p


def test_user_prompt_other_kind_unchanged():
    req = BriefingRequest(kind="savedMoney", context={})
    assert briefing._user_prompt(req).startswith("kind=savedMoney")


def test_build_system_selects_monthly_youth_frames():
    ctx = {"contract": {"type": "월세"}, "finance": {"household": "1인", "under35": True, "firstHome": "아니오"}}
    s = briefing.build_system(ctx)
    assert "사라지는 돈" in s  # 월세 frame 주입
    assert "청년 정책대출" in s  # 청년 frame 주입
    assert "LTV 우대 가능성" not in s  # 생애최초 frame 미주입


def test_build_system_selects_newlywed_firsthome_frames():
    ctx = {"contract": {"type": "전세"}, "finance": {"household": "신혼", "under35": False, "firstHome": "예"}}
    s = briefing.build_system(ctx)
    assert "자산형성" in s  # 신혼 frame
    assert "LTV 우대 가능성" in s  # 생애최초 frame
    assert "청년 정책대출" not in s  # under35=False → 청년 frame 미주입
