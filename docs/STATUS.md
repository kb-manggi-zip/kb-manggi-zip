# 프로젝트 현황 & 로드맵 (한눈에)

> KB 만기상담소 — 전월세 만기 D-90, 3갈래(갱신·이사·매매) 비교 에이전트. (갱신: 2026-07-25)
> 상세: 코드 gap=`backend/STUBS.md` · 규정값 검증=`RESEARCH.md` + `ref/rules_확정값_실데이터반영용.md` · API=`docs/API.md`

## 지금 이 서비스가 도는 방식 (한 줄씩)
- **계산(심장)**: `tools/compare.py` — 3갈래 결정론 계산(rules YAML × 공식). 프론트 `engine/compare.ts`와 **오차 0 동치**(테스트 강제). LLM 무개입.
- **실거래**: 국토부 6개구 **43,531건 → SQLite(`trades.demo.db`)**. 런타임은 DB만 읽음(외부 API 미접촉).
- **에이전트**: `/api/analyze` = LangGraph `intake(상황파악) → compare(계산 tool) → narrate(개인화 LLM)`. Langfuse에 **한 trace로 묶여** 찍힘.
- **개인화 통역**: LLM이 사용자 상황(월세/신혼/청년/생애최초)에 맞춰 설명. 프레임은 `persona_frames.yaml`. **숫자는 계산 결과만 인용**(할루시네이션 0, verify 루프).
- **상품 매칭**: `matcher.py` — `kb_products/*.md`(출처·검증) 규칙 매칭 + LLM 사유.
- **Trust Layer**: 숫자=코드 · 가드레일(권유 차단) · 불확실성 명시 · Langfuse.

## ✅ 완료
| 영역 | 상태 |
|---|---|
| B0 골격 · B1 계산(규제 3겹: 정부LTV+KB한도+스트레스DSR) | ✅ engine 동치 |
| B2 실거래 데이터 (6구 43,531건, DB) | ✅ |
| B3 LangGraph(compare/regions/analyze) + Langfuse(부모 span 그룹화) | ✅ |
| B4 실 Claude 연동 · verify 재생성 루프 · SSE · 개인화 가이드 · matcher RAG | ✅ |
| **규정값 검증 반영** (lending/policy/guarantee, 2026-07-20 대조) | ✅ |
| 인프라: Docker/compose · CI(pytest·ruff·build) · 55 tests green | ✅ |

## ⬜ 다음 (우선순위)
1. **🎬 narrator 개인화** — 하루 시뮬이 fixture(이사=월세로/전세로 동일 씬). LLM/지역별 씬 생성 필요. [B3 STUBS]
2. **🕸 세션 트레이싱** — 지금은 API콜별 trace. 사용자 세션ID를 전 API에 전파 → Langfuse에서 **한 사용자 여정(analyze→regions→products) 하나로** 그룹핑.
3. **🔴 남은 값 검증**(사람) — 생애최초 취득세 감면 일몰 · 중개보수/취득세 구간표 · 규제지역 발표 직전 재확인.
4. **📊 발표 준비** — Langfuse 대시보드 캡처, 데모 시나리오(P2 매매 / P3 월세).
5. (선택) 계약서 Vision(B5) · KB 시세허브(kbland) · 상품 개인화 자격필터(finance 스키마 확장).

## 핵심 결정 로그 (왜 이렇게 했나)
- **규정값 = YAML(DB 아님)**: 소량·저빈도·감사대상 → git diff·PR리뷰·source_url/checked_at 이력이 핵심.
- **에이전틱 = 계산 자율화가 아니라 "상황 이해 + 개인화 통역"**: 숫자는 결정론(안전), LLM은 그 사람 맞춤 설명(LLM 고유값). supervisor는 이 흐름을 명시·추적하는 그릇.
- **MCP/single-agent 미채택**: 숫자 정확성이 생명이라 자율 tool-calling은 리스크. 네이티브 tool-use로 충분(MCP는 과함).
- **스트레스 유형비율 보수적 1.00**: <표2> 원문 미확보 → 근거 없는 추정값 대신 보수 처리(한도 과소추정=안전).
- **매매 지역 = 수도권 규제지역 가정(PoC)**: 데모 동네 전부 서울. assumptions에 명시.

## 여전히 🔴 사람 몫
생애최초 취득세 감면 일몰 · renewal/one_time(임대차법·중개보수·취득세) 미검증 · 규제지역 지정 발표 직전 재확인 · API 키 rotate(노출 이력).
