"""SC-07 하루시뮬 씬 이미지 생성 — docs/하루시뮬_이미지생성_계획.md 실행 스크립트.

⚠️ 실제 비용이 나가는 배치다(OpenAI gpt-image-1, medium quality 기준 장당 약 $0.04 — 정확한
   단가는 실행 시점 OpenAI 요금표 참고).
   .env에 OPENAI_API_KEY 없으면 --run을 줘도 호출하지 않고 에러로 멈춘다.
   기본(인자 없음)은 dry-run — 몇 장을 만들지·예상 비용만 보여주고 API를 호출하지 않는다.

실행:
  python scripts/generate_scene_images.py            # dry-run: 계획·예상비용만 출력(무료, 안전)
  python scripts/generate_scene_images.py --run --limit 5  # 슬러그별 최대 5장만 먼저(프롬프트 톤 확인용)
  python scripts/generate_scene_images.py --run      # 전량 생성(.env OPENAI_API_KEY 필요, 유료 — 사람이 직접 실행)

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

# 태그 → 파일 slug. narrator.py의 _scene_image_url()이 이 파일명 규칙을 그대로 참조한다(단일 소스).
_COMMUTE_SLUG = "commute"
_TAG_SLUG = {
    "음식점·카페 밀집": "cafe",
    "공원 인접": "park",
    "마트·편의점 밀집": "mart",
    "여가시설 밀집": "leisure",
    "학원가": "academy",
}

MODEL = "gpt-image-1"
API_URL = "https://api.openai.com/v1/images/generations"
SIZE = "1024x1536"  # 세로 프레이밍(가장 근접한 지원 비율) — SC-07이 모바일 풀스크린 세로 화면이라
QUALITY = "medium"

# 한국 동네처럼 보이게 하는 공통 건축·거리 요소(사람이 봐도 "한국 골목"이라고 인지할 수 있게).
# 텍스트/간판은 못 넣으니(글자 깨짐·가짜 상호 문제), 건축 요소로 대체.
_KOREA_CUES = (
    "South Korean low-rise mixed-use neighborhood buildings (3-5 stories, gray tile or red brick "
    "facades), exposed gas pipes running along building exteriors, tangled overhead power lines, "
    "narrow street with tightly parked cars, rooftop water tanks on multi-unit villa buildings"
)

# 씬 slug → 프롬프트 서술(인물 없음 — 결정: 씬 간 일관성·페르소나 고정관념 회피).
_SLUG_DESC = {
    "commute": (
        f"early morning golden light, entrance of a Seoul subway station on a quiet residential "
        f"street, {_KOREA_CUES}, calm early-morning mood"
    ),
    "cafe": (
        f"warm midday light, a dense street lined with small cafes and restaurants close together "
        f"with blurred illegible signage and awnings, {_KOREA_CUES}"
    ),
    "park": (
        f"soft daylight, a small neighborhood park with trees and a walking path, {_KOREA_CUES} "
        f"visible along the street bordering the park"
    ),
    "mart": (
        f"early evening light, a small local mart or convenience storefront with blurred illegible "
        f"signage, a delivery scooter parked outside (no rider), {_KOREA_CUES}"
    ),
    "leisure": (
        f"afternoon light, a casual neighborhood street with low-rise leisure-facility storefronts "
        f"(gym, bowling alley, or similar) with blurred illegible signage, {_KOREA_CUES}"
    ),
    "academy": (
        f"afternoon light, a street lined with small low-rise tutoring-academy buildings with "
        f"blurred illegible signage, {_KOREA_CUES}"
    ),
}
_PROMPT_TEMPLATE = (
    "Photorealistic photo, {desc}. No people in frame. No readable text, no logos, no real brand "
    "names or signage. Neutral documentary street-photography style."
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


def _call_openai(prompt: str, api_key: str) -> bytes:
    r = httpx.post(
        API_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": MODEL, "prompt": prompt, "size": SIZE, "quality": QUALITY, "n": 1},
        timeout=120.0,
    )
    r.raise_for_status()
    b64 = r.json()["data"][0]["b64_json"]
    return base64.b64decode(b64)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true", help="실제로 OpenAI API를 호출해 이미지를 생성한다(유료)")
    ap.add_argument(
        "--limit",
        type=int,
        default=None,
        help="슬러그(카테고리)별 최대 N장만 생성 — 전량 돌리기 전 프롬프트 톤 확인용 소량 샘플",
    )
    ap.add_argument(
        "--region",
        type=str,
        default=None,
        help="특정 동만 생성(예: 동선동1가) — 촬영 시나리오 동 하나만 반복 테스트할 때",
    )
    ap.add_argument(
        "--force",
        action="store_true",
        help="이미 파일이 있어도 덮어쓰기 — 프롬프트 다듬으며 같은 동을 재테스트할 때",
    )
    args = ap.parse_args()

    plan = _plan()
    if args.region:
        plan = [(r, s, p) for r, s, p in plan if r == args.region]
        if not plan:
            raise SystemExit(f"'{args.region}' 동에 해당하는 태그가 없습니다(region_enrich.yaml 확인).")
    SCENE_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    if args.force:
        todo = plan
    else:
        todo = [(r, s, p) for r, s, p in plan if not (SCENE_IMAGE_DIR / f"{r}_{s}.png").exists()]
    already = len(plan) - len(todo)

    if args.limit is not None:
        per_slug: dict[str, int] = {}
        capped: list[tuple[str, str, str]] = []
        for region_id, slug, prompt in todo:
            if per_slug.get(slug, 0) >= args.limit:
                continue
            per_slug[slug] = per_slug.get(slug, 0) + 1
            capped.append((region_id, slug, prompt))
        todo = capped
        print(f"--limit {args.limit}: 슬러그(카테고리)별 최대 {args.limit}장으로 제한")

    print(f"전체 계획: {len(plan)}장 (동 {len({r for r, _, _ in plan})}개)")
    print(f"이미 있음: {already}장 / 이번에 생성: {len(todo)}장")
    print(f"예상 비용(gpt-image-1 medium 기준 장당 약 $0.04 추정): 약 ${len(todo) * 0.04:.2f}")

    if not args.run:
        print("\n[dry-run] --run 없이는 API를 호출하지 않았습니다. 실제 생성은 `--run`으로 다시 실행하세요.")
        return

    if not settings.openai_api_key:
        raise RuntimeError(
            ".env 에 OPENAI_API_KEY 가 없습니다 — 실제 비용이 나가는 호출이라 사람이 직접 키를 설정해야 실행됩니다."
        )

    ok, fail = 0, []
    for region_id, slug, prompt in todo:
        out_path = SCENE_IMAGE_DIR / f"{region_id}_{slug}.png"
        try:
            img = _call_openai(prompt, settings.openai_api_key)
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
