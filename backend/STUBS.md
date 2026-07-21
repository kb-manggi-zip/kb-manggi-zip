# STUB · 미구현 지점 목록

> 코드베이스에서 STUB·미구현·단순화·값미확정 지점 전수. (갱신: 2026-07-21)
> ✅ = 이번에 완료. 나머지는 대기.

## A. 실데이터 (Phase B2) — ✅ 완료 (트레이드 DB 파이프라인)
| # | 위치 | 상태 |
|---|---|---|
| A1 | `scripts/refresh/refresh_deals.py` + `tools/molit.py::fetch_trades` | ✅ 국토부 실거래 수집(오프라인) → SQLite → 런타임은 DB만 읽음 |
| A2 | `tools/molit.py::regions_by_branch` + `rules/regions.yaml` sigungu | ✅ 6구 코드+최근6개월 자동 (하드코딩 제거) |
| A3 | `data/region_enrich.yaml` + `aggregate_to_regions(enrich=)` | ✅ 데모 동 좌표/태그 주입 |
| - | `tools/kbland.py::avg_price` | ⬜ KB 데이터허브 STUB (None 반환) |

> ⚠️ `data/trades.demo.db`는 현재 **합성(synthetic) seed** (`scripts/refresh/seed_demo.py`). 실 API 키로 `refresh_deals.py` 실행 후 `cp data/trades.db data/trades.demo.db`로 실데이터 스냅샷 교체 필요.

## B. LLM (Phase B4) — 전부 템플릿/fixture 폴백
| # | 위치 | 상태 |
|---|---|---|
| B1 | `core/llm.py::_call_claude` | ⬜ 실 Claude 호출, `llm_active`(키+`LLM_ENABLED`) 아니면 미실행 |
| B2 | `core/llm.py::generate` | ⬜ `verify.numbers_grounded` 재생성 2회 루프 STUB |
| B3 | `agents/narrator.py` | ⬜ LLM 씬 내레이션 STUB → fixture |
| B4 | `agents/matcher.py` | ⬜ RAG(FAISS)+LLM 사유 STUB → fixture |
| B5 | `agents/briefing.py`·`drafter.py` | ⬜ LLM 경로 게이트 off → 템플릿 |
| B6 | `routers/api.py` briefing | ⬜ SSE 스트리밍 미구현(JSON 반환) |
| B7 | `data/kb_products/*.md` | ⬜ RAG 소스 미작성 |

## C. 오케스트레이션·Vision (seam 파일 존재, 미구현)
- C1 `app/graph.py` LangGraph Supervisor — ⬜ 스켈레톤+주석만 (라우터는 tools·agents 직접 호출) [B3]
- C2 Langfuse 트레이싱 — ⬜ 미연동 (graph.py 구현 시 부착) [B3]
- C3 `app/agents/extractor.py` 계약서 Vision — ⬜ `NotImplementedError` STUB, 엔드포인트 미활성 [B5]

## D. 계산 단순화·가정 (동작은 함)
- D1 매매 지역 = 수도권 규제지역 고정 가정 (`classify_region`은 regions용, compare 미사용)
- D2 기존부채 = 0 고정 (입력 없음)
- D3 DSR 대출유형 = variable 고정 (mixed/periodic 미선택)
- D4 HUG 보증료 = apartment·le80 고정 가정 (주택유형/부채비율 입력 없음)
- D5 취득세 = flat 0.011 + 생애최초 감면 -200만 flat (구간세율·감면요건 정밀화 안 됨)
- D6 중개보수 = flat 0.004 (구간표 아님)
- D7 이사 전세대출 한도 = min(보증금×80%, 2.22억) 단순화 (소득대비 한도 미반영)
- D8 디딤돌 = 무주택 True 가정 (`is_no_house` 입력 없음)
- D9 버팀목 age = `under35` bool을 30/99로 프록시

## E. 규칙값 🔴 미확정 (사람 검증)
- E1 스트레스DSR loan_type_ratio mixed 0.60/periodic 0.30 = 추정 (`lending_regulated.yaml:29`)
- E2 생애최초 취득세 감면 일몰·상한 미확정 (`:49`)
- E3 HUG 요율표 "0.097~0.211%" 개편 계열 대조 필요 (`guarantee_hug.yaml:6`)
- E4 multi_house LTV = PoC 미구현(타깃 외)
- E5 구 `rules/{lending,guarantee,one_time,renewal}.yaml` checked_at: null 전부 미검증

## F. 정리/자투리
- F1 구 `lending.yaml`·`guarantee.yaml`는 매매/보증 경로에서 `lending_regulated`/`guarantee_hug`로 대체됨 (get_rules는 renewal/oneTime용으로만 로드 — 미사용 값 잔존)
- F2 `/api/briefing`은 프론트가 로컬 `briefings.*`로 생성 → 엔드포인트 사실상 미사용(향후 SSE)
- F3 reservation 저장만, 조회/관리 없음
- F4 프론트 테스트 러너 없음 (엔진 검증은 백엔드 동치로 대체)
- F5 `data/regions.py` 더미는 DB 파이프라인으로 대체됨 (fetch_trades가 DB에서 읽음)
