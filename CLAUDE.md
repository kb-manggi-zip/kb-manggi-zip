# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 프로젝트 개요

**KB 만기상담소** — 전월세 만기가 다가온 세입자에게 3갈래(**갱신·이사·매매**)를 계산·비교해주는 데모 앱.

- `frontend/` — **프론트(완성)**. React 18 + Vite 6 + TypeScript + Tailwind v4. Figma Make에서 생성됨.
- `backend/` — **백엔드(B0·B1 완료, 나머지 seam)**. FastAPI + Pydantic v2 + SQLAlchemy. 자세한 건 `backend/README.md`.
- `prompt/백엔드_개발명세서_v1.md` — 백엔드 단계별 명세(Phase B0~B6).
- `ref/KB_만기상담소_기획서_v6_2.md` — "왜"의 근거 기획서. **읽기 전용, 수정·재해석 금지.**
- `docker-compose.yml` (루트) — backend + Postgres.
- `RESEARCH.md` (루트) — 예시값·근사공식·데이터 STUB을 **실제로 교체하는 지점** 목록(리서치 체크리스트).

## 명령어

프론트는 `frontend/` 안에서:

```bash
cd frontend
npm i          # 의존성 설치 (pnpm-workspace.yaml 있으나 lockfile 없음 — npm 사용)
npm run dev    # Vite 개발 서버
npm run build  # 프로덕션 빌드
```

백엔드는 `backend/` 안에서:

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload            # http://localhost:8000/health
pytest                                   # 전체 테스트
TZ=UTC npx tsx scripts/gen_fixtures.mjs  # engine 동치 fixtures 재생성 후 pytest
# 도커(+Postgres): 루트에서 docker compose up --build
```

- **프론트엔 lint / test 스크립트가 없다.** 검증은 `npm run build`(타입체크 포함)로.
- 백엔드 테스트는 `pytest`. **`tests/test_compare_equivalence.py` = 프론트 `engine/`과 오차 0 동치**가 핵심 DoD(fixtures는 위 gen_fixtures.mjs로 생성).

## 아키텍처 (큰 그림)

### 프론트↔백엔드 계약의 중심축
- **`src/api/types.ts` = API 계약서.** 백엔드 Pydantic 모델과 1:1. 필드명·타입·한글 리터럴 유지. 여기 바꿔야 풀리는 문제는 멈추고 사람에게 보고.
- **`src/engine/compare.ts` = 계산 로직의 참조 구현(reference implementation).** 백엔드 `tools/compare.py`는 이 출력과 전 필드 오차 0으로 일치해야 한다. 숫자 로직을 볼 땐 항상 여기가 정답.
- **`src/api/client.ts` = 로컬/원격 seam.** `localOrRemote()` 헬퍼가 `VITE_API_URL` 환경변수 유무로 분기한다:
  - 미설정 → `engine/`·`data/`를 직접 호출(로컬 모드, 데모 백업).
  - 설정 → `${VITE_API_URL}/api/...`로 fetch(에이전트 모드).
  - **목표: `VITE_API_URL` 하나만 켜면 프론트 무수정으로 백엔드 모드 전환.**
- **화면(`screens/`)은 `engine/`·`data/`를 직접 import하면 안 된다.** 반드시 `api/`(client.ts)를 경유. 정적 데이터도 client.ts가 re-export(`PERSONAS`, `SAVED_MONEY_CARDS`, `briefings`, `NOTICE_DEADLINE_MONTHS`).

### 화면 흐름 (라우팅)
- react-router가 의존성에 있으나 **URL 라우팅은 쓰지 않는다.** `src/store.tsx`의 `screen: 'SC-01'..'SC-12'` 상태를 `src/app/App.tsx`의 `switch` Router가 렌더링.
- 흐름: SC-01 홈 → SC-02 계약입력 → SC-12 계산로딩 → SC-03 비교표 → (SC-04 지역/SC-05 월세지역 · SC-06 갱신체크 · SC-07 하루/SC-08 아낀돈 · SC-09 금융패키지) → SC-10 예약 → SC-11 리마인더.
- 분기 로직 일부는 Router에 있음(예: 월세+이사 → `RegionListMonthly`).

### 상태
- `src/store.tsx` — Context + `useReducer` 하나가 전역 상태. `contract`/`finance`/`comparison`/선택값 보관.
- localStorage `kb_app_state`에 자동 persist(단, `screen`은 제외 — 복원 시 항상 SC-01로).

### 규정 수치 (rules)
- 모든 대출/갱신/보증/일회성 비용 수치는 **`src/engine/rules.ts` 한 곳**에. 백엔드는 `rules/*.yaml`.
- **전부 PoC 예시값(`# TODO 검증`)** — 법령·공시 검증은 사람의 몫. 이상해 보여도 고치지 말고 보고.

### 디자인/포맷 관례
- 색·브랜치 색/아이콘 토큰: `src/theme.ts`(`COLORS`, `BRANCH_COLORS`, `BRANCH_ICONS`). 공용 UI 프리미티브: `src/components/ui.tsx`(`MobileShell`(max-width 390 모바일), `PrimaryBtn` 등).
- 금액 포맷은 유틸만 사용(직접 `toLocaleString` 금지): `formatAmount`/`formatMonthly` 등.
  - `src/engine/format.ts`는 2026-07-30 삭제됨(어디서도 import 안 되던 죽은 중복 파일 — `src/utils/format.ts`가 정본). `engine/compare.ts`는 여전히 프론트/백엔드 동치 계약 때문에 자체 `formatAmt`를 따로 가진다(의도된 것, 통합 대상 아님). 백엔드 `tools/format.py`의 `format_amt`/`format_amount` 구분도 이 의도된 분리를 그대로 반영한 것.

### 백엔드 계층 (`backend/app/`)
- **`schemas.py`는 프론트 `types.ts`의 1:1 이식.** 필드명·한글 리터럴·Optional 여부까지 계약. 바꿔야 풀리면 멈추고 보고.
- **`tools/` = 순수 계산(LLM 없음).** `compare.py`가 심장 — `engine/compare.ts`를 줄 단위로 옮긴 것. **JS `Math.round`는 `tools/format.py::js_round`(=`floor(x+0.5)`)로 재현**(Python 기본 `round`는 banker's rounding이라 금지). 날짜는 `dates.py`가 JS `Date`(UTC 파싱·`setMonth` 롤오버) 동치.
- **`agents/` = LLM 노드(seam).** `core/llm.py`가 게이트: `settings.llm_active`(키+`LLM_ENABLED`)가 아니면 **항상 템플릿 폴백**(`agents/templates.py` = `briefings.ts` 이식). 키를 켜도 `verify` 재생성 루프는 아직 STUB(B4).
- **외부 데이터도 seam.** `tools/molit.py`(실거래)·`kbland.py`(KB)는 지금 fixture(`data/`) 반환. 실 API는 반드시 `core/cache.py::@cached`로 감싼다(쿼터 보호).
- **DB는 `DATABASE_URL`로 실체만 교체.** 기본 SQLite 파일, compose에서 Postgres. ORM은 `models/`, 세션은 `core/db.py`.
- 규정 수치는 `rules/*.yaml`에서만 로드(`core/rules.py`). 각 항목 `checked_at: null`이면 로드 시 경고 — 법령 검증은 사람 몫.

---

# 코딩 에이전트 행동 수칙 (명세보다 우선함)

## 멈추고 물어봐야 하는 상황 (임의 진행 금지)
- types.ts / schemas.py 스키마를 바꿔야만 풀리는 문제를 만났을 때
- rules/*.yaml의 수치가 이상하다고 판단될 때 (고치지 말고 보고 — 법령 검증은 사람의 일)
- 명세에 없는 기능이 "있으면 좋겠다"고 생각될 때 (제안은 완료 보고에 적고, 구현은 하지 않는다)
- 테스트가 요구사항과 모순될 때

## 금지 사항
- 테스트를 통과시키기 위해 테스트를 약화하거나 skip 처리하는 것 (구현을 고쳐라)
- 실패를 try/except로 삼켜서 조용히 넘어가는 것 — 실패는 로그와 명시적 에러로
- mock/더미 값을 실제 구현인 척 남겨두는 것 — 임시 구현은 반드시 "# STUB:" 주석 + 완료 보고에 명시
- 명세에 없는 라이브러리 추가 (필요하면 이유와 함께 제안만)
- .env / API 키를 코드·로그·커밋에 노출하는 것
- 기존에 통과하던 테스트를 깨뜨린 채 완료 보고하는 것
- pytest에서 실제 외부 API 호출 (반드시 캐시 fixture 모킹)

## 작업 방식
- 한 세션 = 한 Phase. 그 Phase의 DoD 밖 파일은 건드리지 않는다
- 큰 변경 전에 계획을 3~5줄로 먼저 선언하고 진행
- 커밋 단위 = 논리적 작업 1개, 메시지에 Phase 번호 포함 (예: "B1: renewal 계산기 이식")
- 한글 리터럴('전세'|'월세'|'갱신'|'이사'|'매매' 등)은 영문으로 바꾸지 않는다 (프론트 계약과 깨짐)
- 파일 인코딩 UTF-8 고정

## 완료 보고 형식 (매 세션 필수)
1. 변경 파일 목록 + 한 줄 요약
2. DoD 체크 결과 (통과/실패 명시)
3. 실행 방법 (명령어)
4. STUB·미해결·제안 사항 (없으면 "없음"이라고 명시)
