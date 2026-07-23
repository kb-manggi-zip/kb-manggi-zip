"""generate()의 재생성 루프 — 진짜 Claude 호출 없이 가짜 응답으로 검증.

CLAUDE.md 규칙: pytest에서 실제 외부 API 호출 금지. _call_claude를 monkeypatch로 대체한다.
"""

from app.core import llm as llm_module


def _enable_llm(monkeypatch):
    """settings.llm_active가 True가 되도록 (키 없이) 강제."""
    monkeypatch.setattr(llm_module.settings, "llm_enabled", True)
    monkeypatch.setattr(llm_module.settings, "anthropic_api_key", "fake-key-for-test")


def test_llm_비활성_시_바로_폴백(monkeypatch):
    monkeypatch.setattr(llm_module.settings, "llm_enabled", False)
    result = llm_module.generate(system="x", user="y", fallback=lambda: "폴백 문구")
    assert result == "폴백 문구"


def test_숫자_틀리면_재시도해서_맞는_답_반환(monkeypatch):
    _enable_llm(monkeypatch)
    responses = iter(["월 15만원 차이나요", "월 12만원 차이나요"])
    calls = []

    def fake_call(system, user):
        calls.append(1)
        return next(responses)

    monkeypatch.setattr(llm_module, "_call_claude", fake_call)

    result = llm_module.generate(
        system="x",
        user="y",
        fallback=lambda: "폴백",
        allowed_numbers={12},
    )
    assert result == "월 12만원 차이나요"
    assert len(calls) == 2  # 1차 실패 → 2차 성공


def test_계속_숫자_틀리면_결국_폴백(monkeypatch):
    _enable_llm(monkeypatch)
    calls = []

    def fake_call(system, user):
        calls.append(1)
        return "월 15만원 차이나요"  # 매번 틀린 숫자

    monkeypatch.setattr(llm_module, "_call_claude", fake_call)

    result = llm_module.generate(
        system="x",
        user="y",
        fallback=lambda: "폴백 문구",
        allowed_numbers={12},
    )
    assert result == "폴백 문구"
    assert len(calls) == 3  # 최초 1회 + 재시도 2회, 전부 시도 후 포기


def test_권유_표현이면_재시도(monkeypatch):
    _enable_llm(monkeypatch)
    responses = iter(["무조건 가입하세요!", "조건을 정리해서 안내드려요"])

    def fake_call(system, user):
        return next(responses)

    monkeypatch.setattr(llm_module, "_call_claude", fake_call)

    result = llm_module.generate(system="x", user="y", fallback=lambda: "폴백")
    assert result == "조건을 정리해서 안내드려요"


def test_allowed_numbers_none이면_숫자검증_생략(monkeypatch):
    """하위호환: allowed_numbers 안 넘기는 기존 호출부(briefing/drafter)는 그대로 동작."""
    _enable_llm(monkeypatch)
    monkeypatch.setattr(llm_module, "_call_claude", lambda system, user: "아무 숫자나 999")

    result = llm_module.generate(system="x", user="y", fallback=lambda: "폴백")
    assert result == "아무 숫자나 999"


def test_호출_실패하면_바로_폴백(monkeypatch):
    _enable_llm(monkeypatch)

    def fake_call(system, user):
        raise RuntimeError("네트워크 에러")

    monkeypatch.setattr(llm_module, "_call_claude", fake_call)

    result = llm_module.generate(system="x", user="y", fallback=lambda: "폴백 문구")
    assert result == "폴백 문구"
