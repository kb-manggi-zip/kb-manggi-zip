# 프로젝트 현황 & 로드맵 (한눈에)

> KB 만기상담소 — 전월세 만기 D-90, 3갈래(갱신·이사·매매) 비교 에이전트. (갱신: 2026-07-27)
> 전체 그림=`docs/서비스_E2E_아키텍처.md`(정본) · 코드 gap=`backend/STUBS.md` · 규정값 검증=`RESEARCH.md` · API=`docs/API.md` · 발표=`docs/발표_골든패스_시나리오.md`

## 지금 이 서비스가 도는 방식 (한 줄씩)
- **계산(심장)**: `tools/compare.py` — 3갈래 결정론 계산(rules YAML × 공식, 규제3겹·디딤돌·HUG·취득세구간). 프론트 `engine/compare.ts`와 **오차 0 동치**. LLM 무개입.
- **실거래**: 국토부 6개구 **64,431건(아파트+연립다세대) → SQLite**. 런타임 DB만.
- **명확화(판단·LLM)**: `agents/clarify.py` — 자유입력을 **LLM이 해석(축 제약, 창작 금지)**, 실패/비활성 시 **키워드 폴백**. 모순 감지는 결정론. 반영은 **HITL 확정**(사용자 [반영할게요] 시에만 순위 반영).
- **개인화 조합 레이어**: `tools/persona.py` — 완성 페르소나 → {가중치·소비성향·직장·리소스}를 **한 산출물(PersonaProfile)로 조합**. scoring·narrator가 이 단일 소스를 공유.
- **동네 추천**: 예산 0단계 하드필터 + **선호지역**(구) + **개인화 스코어**(통계근거 가중합, `tools/scoring.py`, note 보정 반영) → top3 + "왜 추천?" 근거.
- **발품(차별점)**: `narrator` — 소비 프로필 + **상권 실집계(소상공인API)** + **통근 실측(ODsay)** + **국토부 실거래 사례** → 개인화 하루 서사(LLM).
- **에이전트**: `/api/analyze` = LangGraph 6노드 `intake → clarify → compare → route → persona → narrate`. Langfuse 한 trace(세션 그룹핑).
- **개인화**: 명확화·스코어 가중치·발품 프레임 전부 **통계/실데이터 근거 + 화면 노출**(블랙박스 아님). 파이프라인 상세: `docs/개인화_파이프라인.md`.
- **Trust Layer**: 숫자=코드 · verify 가드레일(권유·환각 차단) · 근거·출처 노출 · **Langfuse 관측**(6노드 span에 input/output/metadata — 규칙 스냅샷·가중치 조정 전→후·발품 facts·verify 결과 + **HITL 확정 이벤트**).

## ✅ 완료
| 영역 | 상태 |
|---|---|
| B0 골격 · B1 계산(규제 3겹: 정부LTV+KB한도+스트레스DSR) | ✅ engine 동치 |
| B2 실거래 데이터 (6구 43,531건, DB) | ✅ |
| B3 LangGraph(compare/regions/analyze) + Langfuse(부모 span 그룹화) | ✅ |
| B4 실 Claude 연동 · verify 재생성 루프 · SSE · 개인화 가이드 · matcher RAG | ✅ |
| **규정값 검증 반영** (lending/policy/guarantee, 2026-07-20 대조) | ✅ |
| 인프라: Docker/compose · CI(pytest·ruff·build) · 55 tests green | ✅ |

## ⬜ 다음 (우선순위)  — 상세 로드맵: `docs/에이전트_설계_로드맵.md` · 데모: `docs/발표_골든패스_시나리오.md`
1. **📊 발표 준비** — 골든패스(P2 매매/P3 이사) 리허설 + Langfuse 4노드 캡처. [발표_골든패스_시나리오.md]
2. **🔑 실측 키 넣으면 자동완성**(선택) — `ODSAY_API_KEY`→통근 실측, `SBIZ_API_KEY`는 이미 수집됨. [API_키_발급_가이드.md]
3. **오피스텔 rule set**(범위 확장) — 로드맵 §6. (연립다세대 HUG `other` 요율은 2026-07-27 HUG 공식 페이지 대조 완료 ✅)

**✅ 최근 완료**: **만기 결정 리포트(최종 산출물 ①~⑥) + 합성 마이데이터 + 가드레일 Text-to-SQL(authorizer 7종, 지출→compare 단방향)** · **전세가율 리스크 지표(기능④ 격상 — 보증금÷동 매매중위 실거래, 구간판정, 표본<5 미표시)** · **명확화 판단 노드 + 개인화 조합 레이어(clarify·persona, 6노드 그래프)** · 소비 프로필 카드통계 도출(#39) · 발품 3중 그라운딩(상권 실집계 + 통근 조건부 + **국토부 실거래 사례**) · region_facts 상권 API 자동수집 · ODsay 통근(폴백) · 만기 D-day 전화면 유지 · disclaimer · supervisor 라우팅 · 세션 트레이싱 · 규정값 검증.

## 핵심 결정 로그 (왜 이렇게 했나)
- **규정값 = YAML(DB 아님)**: 소량·저빈도·감사대상 → git diff·PR리뷰·source_url/checked_at 이력이 핵심.
- **에이전틱 = 계산 자율화가 아니라 "상황 이해 + 개인화 통역"**: 숫자는 결정론(안전), LLM은 그 사람 맞춤 설명(LLM 고유값). supervisor는 이 흐름을 명시·추적하는 그릇.
- **MCP/single-agent 미채택**: 숫자 정확성이 생명이라 자율 tool-calling은 리스크. 네이티브 tool-use로 충분(MCP는 과함).
- **스트레스 유형비율 보수적 1.00**: <표2> 원문 미확보 → 근거 없는 추정값 대신 보수 처리(한도 과소추정=안전).
- **매매 지역 = 수도권 규제지역 가정(PoC)**: 데모 동네 전부 서울. assumptions에 명시.

## 여전히 🔴 사람 몫
규제지역 지정 발표 직전 재확인 · API 키 rotate(노출 이력).

(생애최초 취득세 감면 일몰·renewal/one_time 미검증은 각각 `ref/잔여리서치_확정_0726.md`·2026-07-27 PR로 검증 완료돼 목록에서 제외)
