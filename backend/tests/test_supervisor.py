"""슈퍼바이저 라우터 — 규칙 세트 선택 + 갈래 현실성 라우팅(결정론)."""

from app.agents import supervisor

CMP = {"branches": [{"branch": "갱신"}, {"branch": "이사"}, {"branch": "매매"}]}


def test_profile_주택_supported_오피스텔_seam():
    assert supervisor.select_profile("주택")["supported"] is True
    assert supervisor.select_profile("오피스텔")["supported"] is False  # 준주택 = seam
    assert supervisor.select_profile("존재안함")["supported"] is True  # 폴백 주택


def test_branch_notes_reflect_situation():
    r = supervisor.route({"renewalUsed": "사용"}, {"under35": True, "firstHome": "예"}, CMP)
    notes = r["branch_notes"]
    assert "갱신" in notes and "갱신권" in notes["갱신"]  # 갱신권 사용 → 제한
    assert "이사" in notes and "청년" in notes["이사"]  # 청년 → 버팀목
    assert "매매" in notes and "생애최초" in notes["매매"]  # 생애최초 → LTV 우대


def test_route_no_flags_when_plain():
    r = supervisor.route({"renewalUsed": "미사용"}, {"under35": False, "firstHome": "아니오"}, CMP)
    assert r["branch_notes"] == {}
    assert r["profile"] == "주택" and r["profile_supported"] is True
    assert r["available_branches"] == ["갱신", "이사", "매매"]
