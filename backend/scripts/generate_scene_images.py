"""SC-07 하루시뮬 씬 이미지 생성 — docs/하루시뮬_이미지생성_계획.md 실행 스크립트.

⚠️ 실제 비용이 나가는 배치다(Gemini 이미지 생성, 표준 요율 기준 장당 약 $0.039).
   .env에 GEMINI_API_KEY 없으면 --run을 줘도 호출하지 않고 에러로 멈춘다.
   기본(인자 없음)은 dry-run — 몇 장을 만들지·예상 비용만 보여주고 API를 호출하지 않는다.

실행:
  python scripts/generate_scene_images.py            # dry-run: 계획·예상비용만 출력(무료, 안전)
  python scripts/generate_scene_images.py --run       # 실제 생성(.env GEMINI_API_KEY 필요, 유료 — 사람이 직접 실행)

멱등: 이미 만들어진 파일(data/scene_images/{regionId}_{slug}.png)은 건너뛴다 — 중단 후 재실행 가능.
"""

import argparse
import base64
import sys
import time
from pathlib import Path

import httpx
import yaml

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402

ENRICH_PATH = BACKEND_ROOT / "data" / "region_enrich.yaml"
SCENE_IMAGE_DIR = BACKEND_ROOT / "data" / "scene_images"
# region_enrich.yaml과 동일 정규화(소수 수기 태그)
_TAG_ALIASES = {"카페거리": "음식점·카페 밀집", "한강공원": "공원 인접"}

# 태그 → 파일 slug. 씬을 실제로 렌더링/서빙하는 코드(narrator.py 등)가 아직 없어
# 여기서는 파일만 만들어둔다 — 런타임 연결은 이미지가 실제로 존재한 뒤 별도 작업.
_COMMUTE_SLUG = "commute"
_TAG_SLUG = {
    "음식점·카페 밀집": "cafe",
    "공원 인접": "park",
    "마트·편의점 밀집": "mart",
    "여가시설 밀집": "leisure",
    "학원가": "academy",
}

MODEL = "gemini-2.5-flash-image"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

# 씬 slug → 프롬프트 서술(인물 없음 — 결정: 씬 간 일관성·페르소나 고정관념 회피).
_SLUG_DESC = {
    "commute": "early morning golden light, a subway station entrance on a quiet Seoul residential street, no people",
    "cafe": "warm midday light, a quiet cafe-and-restaurant-lined street in a Seoul neighborhood, no people",
    "park": "soft daylight, a small neighborhood park with trees and a walking path in Seoul, no people",
    "mart": "early evening light, a small local mart or convenience store front on a Seoul street, no people",
    "leisure": "afternoon light, a casual neighborhood leisure-facility street in Seoul (no signage), no people",
    "academy": "afternoon light, a street lined with small low-rise tutoring-academy buildings in Seoul, no people",
}
_PROMPT_TEMPLATE = (
    "Photorealistic photo, {desc}. No text, no logos, no real signage, no visible brand names, "
    "neutral documentary street-photography style, vertical 9:16 framing."
)


def _load_enrich() -> dict:
    with ENRICH_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _plan() -> list[tuple[str, str, str]]:
    """[(region_id, slug, prompt), ...] — 그 동이 실제로 가진 태그 전부(상위 N개로 자르지 않음).

    이유: 화면엔 3씬만 보이지만(§핵심 구조), 소비신호에 따라 사람마다 다른 태그가 우선될 수 있어
    보유 태그 전부를 미리 만들어둬야 어떤 조합이 와도 이미지가 있다(계획 문서 §스코프·비용).
    """
    enrich = _load_enrich()
    plan: list[tuple[str, str, str]] = []
    for region_id, info in enrich.items():
        tags = {_TAG_ALIASES.get(t, t) for t in (info.get("tags") or [])}
        if "초역세권" in tags or "역세권" in tags:
            plan.append((region_id, _COMMUTE_SLUG, _PROMPT_TEMPLATE.format(desc=_SLUG_DESC[_COMMUTE_SLUG])))
        for tag, slug in _TAG_SLUG.items():
            if tag in tags:
                plan.append((region_id, slug, _PROMPT_TEMPLATE.format(desc=_SLUG_DESC[slug])))
    return plan


def _call_gemini(prompt: str, api_key: str) -> bytes:
    r = httpx.post(
        API_URL,
        params={"key": api_key},
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=60.0,
    )
    r.raise_for_status()
    parts = r.json()["candidates"][0]["content"]["parts"]
    for p in parts:
        inline = p.get("inlineData") or p.get("inline_data")
        if inline:
            return base64.b64decode(inline["data"])
    raise RuntimeError("Gemini 응답에 이미지 파트 없음")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true", help="실제로 Gemini API를 호출해 이미지를 생성한다(유료)")
    args = ap.parse_args()

    plan = _plan()
    SCENE_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    todo = [(r, s, p) for r, s, p in plan if not (SCENE_IMAGE_DIR / f"{r}_{s}.png").exists()]

    print(f"전체 계획: {len(plan)}장 (동 {len({r for r, _, _ in plan})}개)")
    print(f"이미 있음: {len(plan) - len(todo)}장 / 새로 생성: {len(todo)}장")
    print(f"예상 비용(표준 요율 장당 $0.039 기준): 약 ${len(todo) * 0.039:.2f}")

    if not args.run:
        print("\n[dry-run] --run 없이는 API를 호출하지 않았습니다. 실제 생성은 `--run`으로 다시 실행하세요.")
        return

    if not settings.gemini_api_key:
        raise RuntimeError(
            ".env 에 GEMINI_API_KEY 가 없습니다 — 실제 비용이 나가는 호출이라 사람이 직접 키를 설정해야 실행됩니다."
        )

    ok, fail = 0, []
    for region_id, slug, prompt in todo:
        out_path = SCENE_IMAGE_DIR / f"{region_id}_{slug}.png"
        try:
            img = _call_gemini(prompt, settings.gemini_api_key)
            out_path.write_bytes(img)
            ok += 1
            print(f"  ✓ {out_path.name}")
        except Exception as e:
            print(f"  ✗ {region_id}_{slug}: {e}")
            fail.append(f"{region_id}_{slug}")
        time.sleep(0.2)  # 쿼터 여유

    print(f"완료: {ok}개 성공, {len(fail)}개 실패")
    if fail:
        print("실패 목록:", fail)


if __name__ == "__main__":
    main()
