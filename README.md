# KB 만기상담소

> **전월세 계약 만기 D-90. "눌러앉을까, 옮길까, 살까?"**
> AI 에이전트가 **갱신·이사·매매 세 갈래의 돈·삶·위험을 같은 저울에** 올려 비교하고, 어느 쪽을 고르든 KB 금융으로 연결한다.
>
> *KB국민은행 제8회 AI Challenge 출품작 · 청년 주거 금융 도우미*

---

## 무엇인가

대한민국 임차인은 계약 만기마다 세 갈래 앞에 선다 — **갱신**(눌러앉기)·**이사**(옮기기)·**매매**(사기). 각각 보증금·대출·월 부담이 완전히 다른데 **셋을 한 화면에서 비교해주는 곳이 없다.** 부동산 앱은 매물만, 은행 앱은 상품별 한도만 보여준다.

만기일을 입력하면 이 서비스가 세 갈래를 **하나의 비교표**로 계산하고, 각 갈래의 리스크(보증금 반환 위험 등)와 대비 수단(반환보증 보증료)까지 월 부담으로 환산해 같은 저울에 올린다. **결정을 대신하지 않고, 비교를 완성한다.**

**왜 은행인가:** 세 갈래의 공통 변수가 전부 금융(전세대출 연장/신규, 주담대)이다. 비교표의 마지막 칸은 은행만 채울 수 있다.

## 핵심 설계 원칙

- **숫자는 코드가, 말은 LLM이.** 세 갈래 계산은 전부 결정론적 순수 함수(법령·규정 룰 × 공개 데이터). LLM은 표를 "읽어주는" 통역·라우팅만 한다.
- **정직함이 안전장치.** 불확실 요소(갱신 거절 가능성, 실제 심사)는 "확인 필요"로 표기. 결론·권유 문장 없음(가드레일).
- **모든 수치에 근거.** 규정 값은 YAML로 외부화(출처·확인일). 실거래는 공개 API.

## 아키텍처

```
                 VITE_API_URL 하나로 모드 전환
   ┌─────────────┐   미설정→로컬 계산    ┌──────────────────────────┐
   │  frontend   │ ───────────────────► │  브라우저 내 engine/·data/ │  (데모 백업)
   │ React+Vite  │
   │ (완성 UI)   │   설정→원격 호출      ┌──────────────────────────┐
   └─────────────┘ ───────────────────► │  backend (FastAPI)        │
                                        │  tools(순수계산)·agents(LLM)│
                                        │  실거래 SQLite · rules YAML │
                                        └──────────────────────────┘
```

- **API 계약서 = `frontend/src/api/types.ts`** (백엔드 `schemas.py`와 1:1).
- **계산의 정답 = `frontend/src/engine/compare.ts`** — 백엔드 `tools/compare.py`가 이 출력과 **오차 0으로 일치**(동치 테스트로 강제).
- **실거래는 런타임에 외부 API를 안 탄다** — 오프라인 수집(`refresh_deals.py`) → SQLite → 서버는 DB만 읽음(데모 안정성).

## 저장소 구조

```
KB_2026/
├── frontend/            React + Vite + TS 완성 UI (화면 SC-01~SC-12)
├── backend/             FastAPI — 계산·데이터·LLM
│   ├── app/             tools(순수계산) · agents(LLM seam) · core · rules 로더
│   ├── rules/*.yaml     규정 수치 (출처·확인일)
│   ├── scripts/refresh/ 실거래 수집(오프라인) · 데모 스냅샷
│   ├── data/            trades.demo.db(데모) · region_enrich.yaml · kb_products(RAG)
│   ├── tests/           pytest (프론트 engine 동치 포함)
│   ├── README.md        백엔드 상세
│   └── STUBS.md         ← 코드 seam·미구현 목록 (사람이 채울 곳)
├── docs/API.md          ← 백엔드 API 명세 (엔드포인트·스키마·예시)
├── docker-compose.yml   backend + Postgres
├── CLAUDE.md            코딩 에이전트 규칙(헌법) + 아키텍처 요약
├── RESEARCH.md          ← 값·데이터 검증 체크리스트 (사람이 확인할 법령/공시)
└── ref/ · prompt/       기획서 · 개발명세서 (참고, 읽기 전용)
```

## 빠른 시작

### 1) 프론트만 (백엔드 불필요 — 로컬 모드)
```bash
cd frontend
npm i
npm run dev          # http://localhost:5173  (엔진이 브라우저에서 계산)
```

### 2) 백엔드 연결 (에이전트 모드)
```bash
# 터미널 1 — 백엔드
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                 # 그대로도 동작(SQLite + 템플릿 폴백)
python scripts/refresh/seed_demo.py  # 데모 실거래 스냅샷 생성(네트워크 불필요)
uvicorn app.main:app --reload        # http://localhost:8000/health

# 터미널 2 — 프론트 (frontend/.env 에 VITE_API_URL=http://localhost:8000)
cd frontend && npm run dev
```

### 3) 도커 (backend + Postgres)
```bash
docker compose up --build            # backend:8000 · postgres:5432
```

## 테스트
```bash
cd backend && source .venv/bin/activate && pytest        # 34개
# 프론트 engine ↔ 백엔드 compare 동치 재생성:
TZ=UTC npx tsx scripts/gen_fixtures.mjs && pytest
```

## 실데이터·AI 채우기 (뚫어놓은 seam)

지금은 키 없이도 전 기능이 폴백으로 동작한다. 실체만 꽂으면 된다.

| 채울 것 | 위치 | 지금 |
|---|---|---|
| 국토부 실거래 | `scripts/refresh/refresh_deals.py` | ✅ 파이프라인 완성 — `.env` `MOLIT_API_KEY` 넣고 실행 → DB |
| KB 시세·전세가율 | `tools/kbland.py` | ⬜ STUB(Optional) |
| LLM 통역/RAG | `core/llm.py` + `agents/*` | ⬜ 키+`LLM_ENABLED=true` 시 활성, 아니면 템플릿 폴백 |
| 상품 RAG 소스 | `data/kb_products/*.md` | ⬜ 공시 원문 정리(사람) |
| LangGraph·Vision | `app/graph.py` · `agents/extractor.py` | ⬜ seam 스켈레톤 [B3/B5] |
| 규정 수치 검증 | `rules/*.yaml` | ⬜ 예시값 + `checked_at: null` |

- **코드 seam 전체 목록** → [`backend/STUBS.md`](backend/STUBS.md)
- **값·법령·데이터 검증 체크리스트** → [`RESEARCH.md`](RESEARCH.md)
- **백엔드 API 명세** → [`docs/API.md`](docs/API.md)

## 기술 스택
- **프론트**: React 18 · Vite 6 · TypeScript · Tailwind v4 (Figma Make 생성)
- **백엔드**: Python 3.11 · FastAPI · Pydantic v2 · SQLAlchemy · SQLite/Postgres
- **데이터**: 국토부 실거래(PublicDataReader) · 규정 YAML
- **AI(예정)**: Claude API · LangGraph · FAISS · Langfuse

---

> ⚠️ 산출물은 "판단"이 아니라 **"비교표와 시뮬레이션"**이다. 모든 수치는 **참고 추정치**이며 실제 조건은 심사·계약에 따른다. `rules/*.yaml` 의 법령·공시 수치는 **제출 전 원문 검증 필요**(예시값).
