# KB 만기상담소 — 백엔드

전월세 만기 D-90, **세 갈래(갱신·이사·매매)** 를 계산·비교하는 에이전트 백엔드.
프론트(`../frontend`)의 `src/api/types.ts` 가 API 계약서이고, `src/engine/compare.ts` 가
계산의 참조 구현이다. **`VITE_API_URL` 하나만 프론트에 설정하면 무수정으로 이 백엔드로 전환**된다.

## 현재 상태 (Phase)
- ✅ **B0 골격**: schemas(types.ts 1:1) · rules YAML 로더 · @cached · CORS · Dockerfile
- ✅ **B1 계산 심장**: `tools/compare.py` — 프론트 engine 과 **동치 테스트 통과(오차 0)**
- ✅ **B2 실거래**: `tools/molit.py` — 국토부 실거래 6개구 43,531건 반영 완료(2026-07-22), `region_enrich.yaml` 80개 동 좌표 지오코딩 완료
- 🔌 **뚫어놓음(seam)**: 아래는 인터페이스·엔드포인트 완비 + 폴백으로 지금 동작, 실체만 채우면 됨
  - `tools/kbland.py` → KB 데이터 (Phase B2)
  - `app/graph.py` → LangGraph Supervisor (Phase B3, 작업 중)
  - `agents/*` + `core/llm.py` → LLM 통역/RAG (Phase B4). 키 없으면 템플릿 폴백
  - DB → 기본 SQLite, compose 시 Postgres

## 빠른 실행 (도커 없이)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                 # 그대로도 동작 (SQLite + 폴백)
uvicorn app.main:app --reload        # http://localhost:8000/health
```

### 최초 1회만: 커밋 시 자동 포맷(pre-commit) 설정

```bash
# 루트(prev-live/)에서 실행 — .git이 여기 있어서
pre-commit install
```
이후 `git commit`할 때마다 `ruff format`·`ruff check --fix`가 자동으로 돌아요(수동으로 안 돌려도 됨).

## 도커 (Postgres 포함)

```bash
# 프로젝트 루트에서
docker compose up --build            # backend:8000 + postgres:5432
```

## 프론트 연결

```bash
# frontend/.env
VITE_API_URL=http://localhost:8000
# 이후 npm run dev — 로컬 engine 대신 이 백엔드를 호출
# (VITE_API_URL 미설정 = 로컬 모드, 데모 백업)
```

## 테스트

```bash
source .venv/bin/activate
# 프론트 engine 출력을 fixtures로 (동치 테스트 입력). node 필요, 프론트 설치 불필요:
TZ=UTC npx tsx scripts/gen_fixtures.mjs
pytest                               # 단일: pytest tests/test_compare_equivalence.py -q
```

## 구조

```
app/
├── main.py            FastAPI + CORS + startup(init_db, rules)
├── schemas.py         Pydantic — types.ts 1:1 계약 (변경 금지)
├── routers/api.py     엔드포인트 (types.ts 계약)
├── tools/             순수 계산·조회 (LLM 없음)
│   ├── compare.py     ★ 심장 — engine/compare.ts 이식
│   ├── dates.py       D-day·통보기한 (JS Date 동치)
│   ├── format.py      금액 포맷 (JS Math.round 재현)
│   ├── molit.py       실거래 → Region[] (DB에서 읽음, 외부 API 미접촉)
│   ├── trades_store.py 실거래 SQLite 저장/조회 계층
│   └── kbland.py      KB 통계 seam           ← B2에서 채움
├── agents/            LLM 노드 (seam + 템플릿 폴백)  ← B4에서 실호출
├── core/              config · cache · rules(YAML) · db · llm(가드레일) · verify
├── models/            reservation ORM
└── data/              region_enrich.yaml(좌표/태그) · trades.demo.db(데모 스냅샷)
rules/                 lending·renewal·guarantee·one_time·regions·policy_loans·lending_regulated·guarantee_hug .yaml
scripts/refresh/       refresh_deals.py(실 API 수집) · seed_demo.py(합성 스냅샷)
data/kb_products/      RAG 소스 (B4, 사람이 채움)
tests/                 pytest — 특히 프론트 engine 동치
```

## 실거래 데이터 (Phase B2) — 런타임은 DB만 읽음

```bash
# 실데이터 수집 (오프라인, .env MOLIT_API_KEY 필요) — 6구 × 최근 6개월 × 아파트 매매/전월세
python scripts/refresh/refresh_deals.py        # → cache/raw/ + data/trades.db
cp data/trades.db data/trades.demo.db          # 발표 데모 스냅샷 갱신(커밋)

# 키 없이 데모/테스트 (합성 스냅샷)
python scripts/refresh/seed_demo.py            # → data/trades.demo.db
```
- **서버는 외부 API를 호출하지 않는다** — `fetch_trades`가 `data/trades.db`(없으면 `trades.demo.db`)에서만 읽음. 네트워크 끊겨도 `/api/regions` 정상.
- DB가 비면 명확한 에러(“refresh 먼저 실행”). `trades.db`는 gitignore, `trades.demo.db`는 커밋.

## 데이터/LLM을 나중에 채우는 법 (뚫어놓은 지점)

| 채울 것 | 파일 | 지금 상태 |
|---|---|---|
| 국토부 실거래 | `scripts/refresh/refresh_deals.py` | ✅ 완료 (키 꽂고 실행 → DB). 데모는 `seed_demo.py` 합성 스냅샷 |
| KB 통계 | `tools/kbland.py::avg_price` | `None` 반환 STUB |
| LLM 실호출 | `core/llm.py::_call_claude` | `LLM_ENABLED=true` + 키 시 활성 (검증기 B4 후 권장) |
| 상품 RAG | `agents/matcher.py` + `data/kb_products/*.md` | fixture 반환 |
| 규정 수치 검증 | `rules/*.yaml` | 예시값 + `checked_at: null` (사람이 검증) |

> ⚠️ `schemas.py` / `rules/*.yaml` 수치를 바꿔야 풀리는 문제는 **중단하고 보고**. (루트 CLAUDE.md 헌법)
