"""@cached — 2회째 호출은 파일 캐시 적중 (외부 함수 1회만 실행)."""

from app.core import config
from app.core.cache import cached


def test_cache_hits_second_call(tmp_path, monkeypatch):
    monkeypatch.setattr(config.settings, "cache_dir", str(tmp_path))

    calls = {"n": 0}

    @cached(ttl_hours=24)
    def fetch(x):
        calls["n"] += 1
        return {"v": x}

    assert fetch(7) == {"v": 7}
    assert fetch(7) == {"v": 7}  # 캐시 HIT
    assert calls["n"] == 1  # 원 함수는 1회만

    assert fetch(8) == {"v": 8}  # 다른 인자 → MISS
    assert calls["n"] == 2
