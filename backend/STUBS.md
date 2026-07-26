# STUB · 미구현 지점 목록

> 코드베이스에서 STUB·미구현·단순화·값미확정 지점 전수. (갱신: 2026-07-25)
> ✅ = 완료. ⬜ = 대기.

## A. 실데이터 (Phase B2) — ✅ 완료 (트레이드 DB 파이프라인, 실데이터 반영 완료)
| # | 위치 | 상태 |
|---|---|---|
| A1 | `scripts/refresh/refresh_deals.py` + `tools/molit.py::fetch_trades` | ✅ 국토부 실거래 수집(오프라인) → SQLite → 런타임은 DB만 읽음. **`data/trades.demo.db`를 실데이터로 교체 완료**(6개구 43,531건, 2026-07-22) |
| A2 | `tools/molit.py::regions_by_branch` + `rules/regions.yaml` sigungu | ✅ 6구 코드+최근6개월 자동 (하드코딩 제거) |
| A3 | `data/region_enrich.yaml` + `aggregate_to_regions(enrich=)` | ✅ 좌표는 80개 동 전체 카카오맵 지오코딩으로 채움. **tags/source는 원래 수기 8개 동만 있고 나머지 72개는 비어있음 — narrator.py 작업 시 필요하면 수기로 보강할 것** |
| - | `tools/kbland.py::avg_price` | ⬜ KB 데이터허브 STUB (None 반환) |

> ~~⚠️ `data/trades.demo.db`는 현재 **합성(synthetic) seed**~~ → 2026-07-22 국토부 실거래로 교체 완료. 이제 서울 6개구(마포·은평·도봉·성북·노원·중랑) 실데이터.

## B. LLM (Phase B4) — 실 Claude 연동됨 (`.env` `ANTHROPIC_API_KEY`+`LLM_ENABLED=true`)
| # | 위치 | 상태 |
|---|---|---|
| B1 | `core/llm.py::_call_claude` | ✅ 실 Claude 호출 동작 (`llm_active`면 실호출, 아니면 템플릿 폴백) |
| B2 | `core/llm.py::generate` | ✅ `verify.numbers_grounded` 재생성 2회 루프 완료 (권유·숫자 검증) |
| B3 | `agents/narrator.py` | ✅ **씬 YAML 레지스트리**(scenes.yaml, 월세로≠전세로) + ✅ **'온라인 발품' LLM 내레이션**(`narrate_lifestyle`: 동네 실데이터+소비 프로필 `spending_profiles.yaml`, 금액 단정 금지, llm off 폴백). 🟡 `data/region_facts.yaml`(교통·물가·시설)은 seam만 뚫림 — **팀원이 채우는 중**(가이드: docs/지역데이터_채우기_가이드.md). 소비 프로필은 PoC 가정→KB 카드데이터로 교체 seam |
| B4 | `agents/matcher.py` | ✅ 문서(kb_products) 기반 규칙 매칭 + LLM 사유. 개인화 자격필터는 finance 필요(스키마 확장 대기) |
| B5 | `agents/briefing.py`·`drafter.py` | ✅ 실 Claude + **개인화 가이드**(YAML `persona_frames.yaml` 상황별 프레임). drafter도 실호출 |
| B6 | `routers/api.py` briefing | ✅ `/api/briefing/stream` SSE(페이싱 포함). 단 compare 화면은 `/api/analyze`의 briefing 재사용(SSE 미사용) |
| B7 | `data/kb_products/*.md` | ✅ 상품 5종+보장 2종. **✅ 출처·checked_at 2026-07-20 확정 반영** |

## C. 오케스트레이션·Vision
- C1 ✅ `app/graph.py` LangGraph — compare/regions 그래프 + **분석 에이전트 `/api/analyze`(intake→compare→route→narrate 4노드)**. `route`=supervisor 라우팅(규칙 세트 선택+갈래 현실성, `agents/supervisor.py`). 🟡 오피스텔 등 property 라우팅은 seam(주택만 구현) [로드맵 §5]
- C2 ✅ Langfuse 트레이싱 — 전 노드 `@observe` + `analyze_agent` 부모 span으로 **한 trace에 묶음**(OTel 전파 검증). **+ 세션 그룹핑**: 프론트가 여정마다 `X-Session-Id` 헤더 전송 → `core/tracing.py::session_scope`가 `propagate_attributes(session_id=…)`로 root+하위 span 전체에 stamp → Langfuse **Sessions**에서 analyze→regions→simulate→products가 한 여정으로 묶임(스키마 변경 없음, in-memory OTel로 검증).
- C3 ⬜ `app/agents/extractor.py` 계약서 Vision — `NotImplementedError` STUB, 엔드포인트 미활성 [B5]

## D. 계산 단순화·가정 (동작은 함)
- D1 매매 지역 = 수도권 규제지역 고정 가정 (`classify_region`은 regions용, compare 미사용)
- D2 기존부채 = 0 고정 (입력 없음)
- D3 DSR 대출유형 = variable 고정 (mixed/periodic 미선택)
- D4 HUG 보증료 = ✅ **주택유형 입력**(`housingType` 아파트/빌라) → 아파트=apartment / 빌라=other 분기. 부채비율은 le80 고정 가정. 🔴 other(연립·다세대) 요율값 검증 필요(현재 placeholder). 단독다가구·오피스텔은 범위 밖
- D5 ✅ 취득세 = **지방세법 §11 3단계 구간세율**(팀원 PR #22) + 생애최초 감면 -200만. 소형 300만·12억 상한 구분은 PoC 미반영
- D6 ✅ 중개보수 = **구간표**(임대차=서울 조례 / 매매·교환=시행규칙 별표, 팀원 PR #22)
- D7 이사 전세대출 한도 = min(보증금×80%, 2.22억) 단순화 (소득대비 한도 미반영)
- D8 디딤돌 = 무주택 True 가정 (`is_no_house` 입력 없음)
- D9 버팀목 age = `under35` bool을 30/99로 프록시

## E. 규칙값 — ✅ 대부분 검증 완료 (2026-07-20, `ref/rules_확정값_실데이터반영용.md`)
- E1 ✅ 스트레스DSR loan_type_ratio: 추정 0.60/0.30 **제거 → 보수적 1.00**(변동만 사용, 출력 불변)
- E2 ✅ 생애최초 취득세 감면 — **2028.12.31까지 연장 확정**(지특법 §36의3, checked 2026-07-26). 12억↓ 200만 한도, firstHome '예' 매매에 이미 -200만 적용. (소형 300만·12억 상한 구분은 PoC 미반영 = D5)
- E3 ✅ HUG 요율표 리서치_3 **셀 대조 완료·유지 확정** (아파트 0.115%/0.122%/0.128%)
- E4 multi_house LTV = PoC 미구현(타깃 외)
- E5 ✅ `renewal`·`one_time` 전 항목 **검증 완료**(conversion_rate 0.0475 + 나머지 5개, 팀원 PR #22, checked 2026-07-26). 중개보수·취득세는 구간표(D5·D6). **시작 시 미검증 경고 0줄.** 남은 🔴 = 빌라 HUG `other` 요율(D4)
- **검증 완료**: `lending_regulated`·`policy_loans`·`guarantee_hug`.yaml → `checked_at: 2026-07-20`

## F. 정리/자투리
- F1 ✅ 구 `lending.yaml`·`guarantee.yaml` **삭제 완료**(2026-07-26). `get_rules`는 renewal/oneTime만 로드 → 무의미한 미검증 경고 6줄 제거(12→5). 대출/보증 규제값은 `lending_regulated`/`guarantee_hug`에서 직접 로드
- F2 `/api/briefing`은 프론트가 로컬 `briefings.*`로 생성 → 엔드포인트 사실상 미사용(향후 SSE)
- F3 reservation 저장만, 조회/관리 없음
- F4 프론트 테스트 러너 없음 (엔진 검증은 백엔드 동치로 대체)
- F5 `data/regions.py` 더미는 DB 파이프라인으로 대체됨 (fetch_trades가 DB에서 읽음)
