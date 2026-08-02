"""SC-07 하루시뮬 씬 이미지 생성 — docs/하루시뮬_이미지생성_계획.md 실행 스크립트.

⚠️ 실제 비용이 나가는 배치다(Gemini API, 장당 비용은 실행 시점 요금표 참고).
   .env에 GEMINI_API_KEY 없으면 --run을 줘도 호출하지 않고 에러로 멈춘다.
   기본(인자 없음)은 dry-run — 몇 장을 만들지·예상 비용만 출력하고 API를 호출하지 않는다.

동마다 따로 만들지 않는다(2026-08-02 설계 변경): 카테고리×시간대별로 풀(POOL_SIZE장)만 만들어두고,
narrator.py가 동 이름 해시로 그 동에 풀 중 한 장을 고정 배정한다(agents/narrator.py::_scene_image_url
참고 — 같은 상수 POOL_SIZE를 이 파일에도 복제해 단일 소스로 유지, 둘 다 바뀌면 같이 바꿀 것).

Gemini만 사용(2026-08-02, ChatGPT/OpenAI 미사용 확정) — Google AI Studio API 키 하나로 동작,
9:16 세로 비율 프리셋이 있어 SC-07 모바일 프레임에 더 잘 맞음.

실행:
  python scripts/generate_scene_images.py                     # dry-run: 계획·예상비용만 출력(무료, 안전)
  python scripts/generate_scene_images.py --run --limit 1     # 풀당 1장만 먼저(프롬프트 톤 확인용)
  python scripts/generate_scene_images.py --run --slug cafe   # 카페 카테고리만
  python scripts/generate_scene_images.py --run               # 전량 생성(.env GEMINI_API_KEY 필요, 유료)

멱등: 이미 만들어진 파일(data/scene_images/{slug}_{시간대}_{i}.png)은 건너뛴다 — 중단 후 재실행 가능.
"""

import argparse
import base64
import sys
import time
from pathlib import Path

import httpx

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402

SCENE_IMAGE_DIR = BACKEND_ROOT / "data" / "scene_images"

# agents/narrator.py::_POOL_SIZE와 반드시 같은 값 유지(단일 소스 표기, 실제 공유는 안 됨 — 둘 다 수기 동기화).
# 카테고리×시간대별 1장씩만 만들 계획이라 1로 고정(2026-08-02) — 총 16장(commute 1 + 나머지 5개×3).
# 나중에 다양성을 늘리고 싶으면 값을 올리고 풀을 더 채우면 됨 — 파일 없는 variant는 그라디언트로 폴백.
POOL_SIZE = 1

# Google AI Studio(개발자 API 키, 프로젝트/리전 설정 불필요) — generateContent에 이미지 파트로 응답.
MODEL = "gemini-3.1-flash-image"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
ASPECT_RATIO = "9:16"  # SC-07 모바일 프레임(≈9:19.5)에 가장 가까운 프리셋
COST_PER_IMAGE = 0.04  # 추정 — 정확한 단가는 실행 시점 Gemini API 요금표 참고

_COMMON = (
    "포토리얼리스틱 사진, 자연스러운 다큐멘터리 스트리트 포토(필름 그레인·빈티지 필터 없음). "
    "세로 9:16 비율의 세로 사진(휴대폰 세로 화면 꽉 채움, 가로로 넓은 사진 아님) — 카메라가 피사체에서 "
    "충분히 뒤로 물러난 와이드 구도로, 위로는 하늘까지, 아래로는 인도·바닥까지 세로 프레임 안에 다 "
    "들어오게. 눈높이 카메라 앵글, 자연스러운 구도. 낡거나 색바랜 느낌, 빈티지 느낌 없음. 사람이 단 "
    "한 명도 등장하지 않음(매장 직원·행인 포함, 예외 없음)."
)

# 상점·간판이 등장하는 카테고리에만 붙는 문구(공원처럼 상가가 없어야 하는 씬엔 절대 섞이면 안 됨 —
# 예전엔 _COMMON에 있어서 park에도 상가 건물이 강제로 끼어드는 버그가 있었음, 2026-08-02 분리).
_STOREFRONT = (
    "밝고 깨끗한, 최근 지어지거나 리모델링된 저층~중층(3~5층) 한국 상가 건물. 간판·안내판은 색·재질·"
    "조명이 있는 평범한 상점 간판 형태 그대로 보이되, 그 위의 글자·로고·브랜드명만 흐릿하게 뭉개지거나 "
    "각도상 가려져서 읽을 수 없게(간판 자체가 새하얗거나 텅 빈 판으로 보이면 안 됨, 색이 있는 정상적인 "
    "간판이 거기 걸려있는 느낌은 유지) — 단, 업종을 한눈에 알아볼 수 있는 사물·집기·구조물은 또렷하게 "
    "보이게 유지(글자를 없앤다고 업종 정체성까지 흐려지면 안 됨). 낡거나 벗겨진 벽돌, 색바랜 페인트, "
    "오래된 간판 서체, 좁고 어두운 골목(일본식 좁은 상점가 느낌) 없음."
)
_STOREFRONT_SLUGS = {"cafe", "mart", "leisure", "academy"}

# _COMMON의 "사람 없음"에 대한 유일한 예외(2026-08-02) — 학원가 하원 시간대 특유의 북적임을 위해
# 학생 실루엣만 소량 허용. 해당 씬 서술에 실제로 인물이 등장하는 (slug, bucket)만 여기 등록.
_ALLOW_DISTANT_PEOPLE = {("academy", "evening")}
_PEOPLE_OVERRIDE = (
    "위 '사람 없음' 지침의 유일한 예외로, 방금 서술된 학생 실루엣만 허용(그 외 추가 인물 없음, "
    "얼굴·손 디테일 없이 작고 먼 원경으로만)."
)

# _STOREFRONT의 "글자를 흐릿하게" 지침에 대한 예외(2026-08-02) — "지우되 정상으로 보이게"라는
# 애매한 주문을 주면 모델이 알아볼 수 없는 가짜 글자(낙서 같은 문자)를 만들어서 오히려 더 이상하게
# 나옴(실측). 씬 서술에 구체적 가상 상호명을 직접 박아준 (slug, bucket)만 여기 등록 — 실존 브랜드와
# 겹치지 않는 이름만 사용.
_EXPLICIT_SIGN_SCENES = {
    ("cafe", "morning"),
    ("mart", "morning"),
    ("mart", "day"),
    ("mart", "evening"),
}
_SIGN_TEXT_OVERRIDE = (
    "위 간판 글자를 흐릿하게 처리하라는 지침의 예외로, 방금 서술된 간판 글자만 읽을 수 있게 보이게 "
    "함(다른 배경 간판은 기존 지침대로 흐릿하게). 단, 그래픽 디자인처럼 밋밋하고 완벽하게 평평한 "
    "벡터 폰트로 보이면 안 됨 — 실제 촬영된 간판처럼 재질감(아크릴·금속 채널문자 등)과 조명 반사, "
    "카메라 각도에 따른 약간의 원근 왜곡이 자연스럽게 있어야 함."
)

# 시간대별 강한 시각 차별화 — "부드러운 조명" 같은 추상적 형용사만으론 AI가 아침/낮/저녁을 확실히
# 다르게 안 그려서(테스트로 확인됨), 하늘색·그림자 길이·가로등 on/off 같은 구체적 사물로 명시한다.
# 모든 카테고리에 동일하게 적용(단일 소스) — _plan()이 각 장면 서술 뒤에 자동으로 붙인다.
_TIME_DESC = {
    "morning": "옅은 파스텔톤의 이른 아침 하늘, 낮게 뜬 해로 그림자가 길게 드리워짐, 가로등은 꺼져있음.",
    "day": "쨍하고 밝은 한낮의 파란 하늘, 해가 높이 떠 그림자가 거의 지지 않음.",
    "evening": "주황빛으로 물든 노을 하늘, 그림자가 길고 따뜻한 색조, 가로등과 상점 조명이 켜져있음.",
}

# {slug: {time_bucket: 장면 서술(시간대 문구 제외 — _TIME_DESC가 자동으로 붙음)}}
# narrator.py의 _TAG_SLUG/_COMMUTE_SLUG와 동일 slug 이름 사용(단일 소스).
# commute는 항상 아침 자리에만 배치되므로 morning만 존재.
_SCENES: dict[str, dict[str, str]] = {
    "commute": {
        "morning": (
            "인도 위에 서서 지하철역 출입구를 바라보는 장면 — 카메라는 도로가 아니라 인도 위에 있고, "
            "지하철 계단은 인도 한쪽 가장자리(연석 옆)에 붙어 있으며 도로는 그 옆으로 나란히 지나갈 "
            "뿐 계단이 도로 한복판이나 중앙분리대에 있으면 절대 안 됨(인도 위 시설물로서 사실적인 "
            "위치). 초록 난간의 지하철 계단 입구 바로 위쪽 난간에,지하철 역 이름은 보여지지 않음 "
            "별도의 큰 표지판·기둥·전광판을 새로 만들지 말기. 너무 낡지 않은실제 존재하는 서울 지하철 이미지 반영."
            "노란 점자블록, 은행나무 가로수, 저 멀리 고층 아파트 단지 실루엣. 프레임 "
            "안에 상점 간판·상호가 보이지 않게(지하철역 시설물과 대로변 풍경만, 상점 있는 배경 없음)."
        ),
    },
    "cafe": {
        # 시간대마다 실제 업종 비중이 다르게(아침=카페 위주, 점심=카페+식당 둘 다, 저녁=식당 위주) —
        # 조명만 바꾸는 것보다 장면 내용 자체가 달라져야 시간대별로 뻔히 다르게 보인다.
        "morning": (
            "카페들이 늘어선 평범한 동네 거리, 통유리 매장들 — 가장 가까이 보이는 카페 정면 간판엔 "
            "'모먼트커피'라는 글자가 선명하게 적혀있음. 커피를 사러 나온 이른 아침이라 카페만 문을 "
            "열어 불이 켜져 있고, 옆의 식당들은 셔터가 내려가 있고 그 간판들은 멀리서 봐도 글자가 "
            "안 읽힐 만큼 확실히 흐릿하거나 작게 처리(옆 가게 상호가 또렷하게 읽히면 안 됨)."
        ),
        "day": (
            "평범한 동네 상가 거리, 통유리 매장들 — 점심시간이라 카페·식당 "
            "모두 영업 중, 야외 테이블·의자가 펼쳐져 있고 매장 입간판이 나와있음(글자 없이)."
            "실제 존재하는 식당 이름 참고하기, 간판 이름 잘 안보이게 블러처리, 간판은 3개만 보이게",
            "진짜 카페 식당이 모여있는 공간 느낌이 나되 깔끔된 느낌",
        ),
        "evening": (
            "식당들이 늘어선 평범한 동네 거리, 통유리 매장들 — 저녁 식사 시간이라 식당들이 환하게 불을 "
            "켜고 영업 중, 옆의 카페들은 문을 닫아 불이 꺼져 있음."
        ),
    },
    "mart": {
        # 편의점(CU) 대신 진짜 '동네 마트' 시각 문법으로 전환(2026-08-02) — 과일·채소 매대, 카트, "
        # 생수·라면 박스 등 편의점과 뚜렷이 구분되는 요소로 정체성을 표현. 실존 브랜드 없이 제네릭 이름.
        "morning": (
            "작은 동네 마트 매장이 화면 중심 — 통유리 출입문 위 간판엔 '행복마트'라는 글자가 선명하게 "
            "적혀있음(간판 크기는 실제 마트처럼 적당히 작고 차분함, 건물을 다 가릴 만큼 크지 않음), "
            "양옆 다른 매장들의 간판은 화면에 작게 걸치거나 각도상 흐릿하게 보여서 글자가 읽히지 "
            "않음(억지로 텍스트를 만들어내지 않음). 매장 앞엔 아직 진열 중인 빈 과일·채소 매대 상자들, "
            "접힌 파라솔, 카트 한두 대, 셔터를 막 올려 영업을 시작하는 이른 아침 느낌."
        ),
        "day": (
            "작은 동네 마트 매장이 화면 중심 — 통유리 출입문 위 간판엔 '행복마트'라는 글자가 선명하게 "
            "적혀있음(간판 크기는 실제 마트처럼 적당히 작고 차분함, 건물을 다 가릴 만큼 크지 않음), "
            "양옆 다른 매장들의 간판은 화면에 작게 걸치거나 각도상 흐릿하게 보여서 글자가 읽히지 "
            "않음(억지로 텍스트를 만들어내지 않음). 매장 앞엔 과일·채소가 상자째 진열된 매대, 생수·"
            "라면 박스 더미, 카트 몇 대가 늘어서 있는 한낮의 활기찬 모습."
        ),
        "evening": (
            "작은 동네 마트 매장이 화면 중심 — 통유리 출입문 위 간판엔 '행복마트'라는 글자가 선명하게 "
            "적혀있음(간판 크기는 실제 마트처럼 적당히 작고 차분함, 건물을 다 가릴 만큼 크지 않음), "
            "양옆 다른 매장들의 간판은 화면에 작게 걸치거나 각도상 흐릿하게 보여서 글자가 읽히지 "
            "않음(억지로 텍스트를 만들어내지 않음). 매장 앞엔 정리된 과일·채소 매대와 카트, 형광등이 "
            "환하게 켜져 어두워진 거리 속에서 매장만 밝게 두드러짐."
        ),
    },
    "park": {
        "morning": (
            "작은 동네 근린공원의 포장된 산책로와 잔디 광장 — 나무 몇 그루와 벤치 하나, 한쪽엔 야외 "
            "운동기구(허리돌리기 기구 등) 한두 개, 나무들 사이 저 멀리로 아파트 단지 지붕 라인이 살짝 "
            "보임, 아직 옅은 안개가 살짝 남아있는 고요한 느낌. 프레임 안에 상가·간판·상점은 전혀 "
            "보이지 않되, 울창한 숲이나 등산로 느낌은 아닌 도심 속 근린공원 풍경."
        ),
        "day": (
            "작은 동네 근린공원의 포장된 산책로와 잔디 광장 — 나무 몇 그루와 벤치 하나, 한쪽엔 야외 "
            "운동기구(허리돌리기 기구 등) 한두 개, 나무들 사이 저 멀리로 아파트 단지 지붕 라인이 살짝 "
            "보임. 나뭇잎 사이로 햇살이 뚜렷하게 비침. 프레임 안에 상가·간판·상점은 전혀 보이지 않되, "
            "울창한 숲이나 등산로 느낌은 아닌 도심 속 근린공원 풍경."
        ),
        "evening": (
            "작은 동네 공원 입구 — 나무들과 산책로, 공원 가로등이 하나둘 켜지기 시작함, 벤치 하나. "
            "프레임 안에 상가·간판·상점은 전혀 보이지 않는 순수한 녹지 풍경."
        ),
    },
    "leisure": {
        # 데이터 원본 대분류가 '여가/스포츠/관광/오락'이라 넓은 카테고리지만(refresh_regions.py 주석
        # 참고 — 노래방·볼링장·당구장·PC장·영화관 등도 포함), 실측: 한 프롬프트에 헬스장+노래방+볼링장을
        # 같이 서술하면 "노래방" 단어가 네온·어두운 실내 쪽으로 개념을 끌어가서 헬스장을 의도해도
        # 노래방처럼 나옴. 대신 한 건물에 층별로 다른 여가 업종을 쌓아 다양성을 표현(2026-08-02).
        "morning": (
            "한 건물에 서점, 요가 스튜디오, 헬스장이 차례로 입주한 저층 상가 건물 — "
            "이른 아침이라 1층 서점만 불이 켜져 있고, 2·3층 통유리 너머는 아직 어둡고 조용함.",
            "간판 이름은 그냥 서점, 요가 스튜디오, 헬스장",
        ),
        "day": (
            "한 건물에 서점, 요가 스튜디오, 헬스장이 차례로 입주한 저층 상가 건물 — "
            "한낮이라 세 층 모두 환하게 불이 켜져, 통유리 너머로 책장, 요가매트, 운동기구가 "
            "각각 또렷하게 보임."
            "간판 이름은 그냥 서점, 요가 스튜디오, 헬스장"
        ),
        "evening": (
            "한 건물에 서점, 요가 스튜디오, 헬스장이 차례로 입주한 저층 상가 건물 — "
            "퇴근 후 시간대라 세 층 모두 환하게 불이 켜져 북적이는 느낌, 통유리 너머로 1층 책장, 2층 "
            "요가매트, 3층 운동기구가 각각 뚜렷하게 두드러져 보임."
            "간판 이름은 그냥 서점, 요가 스튜디오, 헬스장"
        ),
    },
    "academy": {
        # 간판 글자를 안 보이게 하니, 한국에서 학원가를 한눈에 알아보게 하는 노란 학원 통학버스·교실
        # 집기(책상·화이트보드)·건물 외벽에 다닥다닥 붙은 세로형 간판 다수로 업종 정체성을 대체한다.
        # 사람은 원칙적으로 없지만, 학원가 특유의 '북적임'을 위해 예외적으로 먼 거리 실루엣만 소량
        # 허용(2026-08-02, _ALLOW_DISTANT_PEOPLE_SLUGS로 처리 — 클로즈업 얼굴·손 디테일 없음).
        "morning": (
            "작은 학원들이 여러 층에 입주한 저층~중층 건물이 늘어선 거리, 건물 외벽엔 세로로 긴 학원 "
            "간판 여러 개가 층마다 다닥다닥 붙어있음(전형적인 한국 학원가 외관) — 건물 앞에 노란색 학원 "
            "통학버스 한 대가 정차해 있고, 등원 전이라 건물 위층들은 대부분 불이 꺼진 채 조용함."
        ),
        "day": (
            "작은 학원들이 여러 층에 입주한 저층~중층 건물이 늘어선 거리, 건물 외벽엔 세로로 긴 학원 "
            "간판 여러 개가 층마다 다닥다닥 붙어있음(전형적인 한국 학원가 외관) — 1층 학원 로비 통유리 "
            "너머로 책상 줄과 화이트보드가 보이고, 몇몇 층에만 불이 켜진 한산한 낮 시간대."
        ),
        "evening": (
            "작은 학원들이 여러 층에 입주한 저층~중층 건물이 늘어선 거리, 건물 외벽엔 세로로 긴 학원 "
            "간판 여러 개가 층마다 다닥다닥 붙어있음(전형적인 한국 학원가 외관) — 하원 시간대라 거의 "
            "모든 층 창문에 불이 켜져 북적이는 느낌, 건물 앞엔 노란색 학원 통학버스 한 대가 다시 정차해 "
            "있고 책가방을 멘 학생 한둘이 버스에 타려고 서 있음(멀리서 본 작은 실루엣, 얼굴·손 디테일 "
            "없이 뒷모습이나 원경으로만)."
        ),
    },
}


def _plan(pool_size: int, only_slug: str | None) -> list[tuple[str, str, int, str]]:
    """[(slug, time_bucket, variant_idx, prompt), ...] — 카테고리×시간대별 풀만 계획(동 순회 없음)."""
    plan: list[tuple[str, str, int, str]] = []
    for slug, buckets in _SCENES.items():
        if only_slug and slug != only_slug:
            continue
        for bucket, desc in buckets.items():
            storefront = f"{_STOREFRONT} " if slug in _STOREFRONT_SLUGS else ""
            people_override = f" {_PEOPLE_OVERRIDE}" if (slug, bucket) in _ALLOW_DISTANT_PEOPLE else ""
            sign_override = f" {_SIGN_TEXT_OVERRIDE}" if (slug, bucket) in _EXPLICIT_SIGN_SCENES else ""
            prompt = f"{_COMMON} {storefront}{desc} {_TIME_DESC[bucket]}{people_override}{sign_override}"
            for i in range(pool_size):
                plan.append((slug, bucket, i, prompt))
    return plan


def _call_gemini(prompt: str, api_key: str) -> bytes:
    r = httpx.post(
        API_URL,
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"],
                "imageConfig": {"aspectRatio": ASPECT_RATIO},
            },
        },
        timeout=120.0,
    )
    if r.is_error:
        raise RuntimeError(f"{r.status_code} {r.reason_phrase}: {r.text}")
    for part in r.json()["candidates"][0]["content"]["parts"]:
        if "inlineData" in part:
            return base64.b64decode(part["inlineData"]["data"])
    raise RuntimeError("Gemini 응답에 이미지 파트가 없습니다(안전 필터 차단 가능성) — 응답 원문 확인 필요")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true", help="실제로 Gemini API를 호출해 이미지를 생성한다(유료)")
    ap.add_argument(
        "--limit",
        type=int,
        default=None,
        help=f"풀 크기를 이 값으로 줄여서 생성(기본 POOL_SIZE={POOL_SIZE}) — 먼저 소량 테스트할 때",
    )
    ap.add_argument("--slug", type=str, default=None, help="특정 카테고리만(commute/cafe/mart/park/leisure/academy)")
    ap.add_argument("--force", action="store_true", help="이미 파일이 있어도 덮어쓰기 — 프롬프트 다듬으며 재테스트")
    ap.add_argument(
        "--print",
        dest="print_prompts",
        action="store_true",
        help="API 호출 없이 카테고리×시간대별 프롬프트 전문을 출력(제미나이 등에 직접 복붙할 때). "
        "--run과 무관하게 이것만 실행하고 종료.",
    )
    args = ap.parse_args()

    if args.slug and args.slug not in _SCENES:
        raise SystemExit(f"알 수 없는 slug '{args.slug}' — 사용 가능: {', '.join(_SCENES)}")

    pool_size = args.limit if args.limit is not None else POOL_SIZE
    plan = _plan(pool_size, args.slug)

    if args.print_prompts:
        seen: set[tuple[str, str]] = set()
        for slug, bucket, _i, prompt in plan:
            if (slug, bucket) in seen:
                continue  # 풀 내 variant는 현재 동일 프롬프트 텍스트 재사용 — 중복 출력 생략
            seen.add((slug, bucket))
            print(f"=== {slug} / {bucket} ===")
            print(prompt)
            print()
        return

    SCENE_IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    if args.force:
        todo = plan
    else:
        todo = [
            (slug, bucket, i, prompt)
            for slug, bucket, i, prompt in plan
            if not (SCENE_IMAGE_DIR / f"{slug}_{bucket}_{i}.png").exists()
        ]
    already = len(plan) - len(todo)

    print(f"전체 계획: {len(plan)}장 (풀 크기 {pool_size}장/카테고리·시간대)")
    print(f"이미 있음: {already}장 / 이번에 생성: {len(todo)}장")
    cost = len(todo) * COST_PER_IMAGE
    print(f"예상 비용(장당 약 ${COST_PER_IMAGE} 추정, 정확한 단가는 실행 시점 요금표 참고): 약 ${cost:.2f}")

    if not args.run:
        print("\n[dry-run] --run 없이는 API를 호출하지 않았습니다. 실제 생성은 `--run`으로 다시 실행하세요.")
        return

    if not settings.gemini_api_key:
        raise RuntimeError(
            ".env 에 GEMINI_API_KEY 가 없습니다 — 실제 비용이 나가는 호출이라 사람이 직접 키를 설정해야 실행됩니다."
        )

    ok, fail = 0, []
    for slug, bucket, i, prompt in todo:
        out_path = SCENE_IMAGE_DIR / f"{slug}_{bucket}_{i}.png"
        try:
            img = _call_gemini(prompt, settings.gemini_api_key)
            out_path.write_bytes(img)
            ok += 1
            print(f"  ✓ {out_path.name}")
        except Exception as e:
            print(f"  ✗ {slug}_{bucket}_{i}: {e}")
            fail.append(f"{slug}_{bucket}_{i}")
        time.sleep(0.2)  # 쿼터 여유

    print(f"완료: {ok}개 성공, {len(fail)}개 실패")
    if fail:
        print("실패 목록:", fail)


if __name__ == "__main__":
    main()
