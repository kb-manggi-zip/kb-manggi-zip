"""파일 기반 캐시 데코레이터.

- 모든 외부 API 응답은 파일로 캐싱한다 (cache/, key=함수명+파라미터 해시).
- 데모는 캐시만으로 완주 가능해야 한다 (쿼터 보호).
- TTL 만료 시 재호출.
"""
import functools
import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Callable

from .config import settings

log = logging.getLogger("kb.cache")


def _key(func_name: str, args: tuple, kwargs: dict) -> str:
    raw = json.dumps(
        {"fn": func_name, "args": args, "kwargs": kwargs},
        sort_keys=True,
        default=str,
        ensure_ascii=False,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def cached(ttl_hours: int | None = None, subdir: str | None = None):
    """외부 조회 함수에 붙이는 파일 캐시. JSON 직렬화 가능한 반환값 전제.

    subdir: cache/<subdir>/ 아래에 저장 (예: 'raw' → API 원응답).
    """

    def deco(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            ttl = settings.cache_ttl_hours if ttl_hours is None else ttl_hours
            cache_dir = Path(settings.cache_dir)
            if subdir:
                cache_dir = cache_dir / subdir
            cache_dir.mkdir(parents=True, exist_ok=True)
            key = _key(func.__qualname__, args, kwargs)
            path = cache_dir / f"{func.__name__}_{key}.json"

            if path.exists():
                age_h = (time.time() - path.stat().st_mtime) / 3600
                if age_h < ttl:
                    log.debug("cache HIT %s", path.name)
                    with open(path, encoding="utf-8") as f:
                        return json.load(f)

            log.debug("cache MISS %s", path.name)
            result = func(*args, **kwargs)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False)
            return result

        return wrapper

    return deco
