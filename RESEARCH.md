# 리서치 체크리스트 — 예시값·근사공식·데이터를 실제로 교체하는 지점

이 문서는 **"지금 예시값/근사/STUB인 것"을 실제 법령·공시·데이터로 갈아끼우는 작업 목록**이다.
코드는 전부 뚫려 있고(인터페이스·파이프라인·테스트 완성), 아래 각 항목의 **값·매핑만 채우면** 실서비스가 된다.

## 대원칙 (작업 전 필독)
1. **수치의 진위는 사람이 검증한다.** 코딩 에이전트는 값을 지어내지 않는다. 각 항목에 `source_url`·`checked_at`을 남긴다.
2. **규정 수치 바꾸는 곳은 `rules/*.yaml` 한 곳** (하드코딩 금지).
3. **계산 공식 자체를 바꾸면 프론트·백엔드 양쪽을 같이 고친다:**
   `frontend/src/engine/compare.ts` (참조 구현) **와** `backend/app/tools/compare.py` (이식본).
   → 고친 뒤 반드시:
   ```bash
   cd backend && TZ=UTC npx tsx scripts/gen_fixtures.mjs && pytest
   ```
   (fixtures를 프론트 기준으로 다시 뜨고 동치 테스트 통과 확인)
4. **외부 API는 `@cached`로 감싼 채로** 붙인다 (쿼터 보호, 데모는 캐시로 완주).

---

## PART A. 규정 수치 (rules/*.yaml) — 값만 검증·교체

> 위치: `backend/rules/*.yaml`. 각 항목 `value` 교체 + `source_url`·`checked_at` 채우기.
> 프론트 `frontend/src/engine/rules.ts`의 같은 값도 함께 맞춘다(동치 유지).

| # | 파라미터 (파일) | 현재 예시값 | 무엇 | 출처(공식) | 확인 포인트 |
|---|---|---|---|---|---|
| A1 | `increase_cap` (renewal) | 0.05 | 계약갱신 인상률 상한 | 주택임대차보호법 (국가법령정보센터) | 지자체 조례 하향분 존재 여부 |
| A2 | `conversion_rate` (renewal) | 0.055 | 전월세전환율 | 한국은행 기준금리 + 대통령령 이율 | 시점별 변동 — 산식(기준금리+이율) 확인 |
| A3 | `notice_deadline_months` (renewal) | 2 | 갱신 의사 통보 기한(만기 N개월 전) | 주택임대차보호법 | 개정 이력 |
| A4 | `ltv` (lending) | 0.70 | 담보인정비율 | 금융위 | 지역·주택유형·생애최초별 상이 → 대표값 정책 결정 |
| A5 | `dsr_cap` (lending) | 0.40 | 총부채원리금상환비율 상한 | 금융위 | 스트레스 DSR 도입분 반영 |
| A6 | `stress_rate` (lending) | 0.045 | 스트레스(가산) 금리 | 은행연합회/금융위 | 스트레스DSR 가산폭 최신치 |
| A7 | `years` (lending) | 30 | 주담대 상환기간(년) | — | 정책상품별 만기 |
| A8 | `jeonse_rate` (lending) | 0.038 | 전세대출 평균 금리 | 은행연합회 공시 | 최신 평균/우대 반영 |
| A9 | `fee_rate` (guarantee) | 0.0015 | 반환보증 보증료율(연) | HUG/HF/SGI 공시 | **주택유형·보증기관별 상이** — 대표값 근거 |
| A10 | `move_base` (one_time) | 1,500,000 | 이사 기본 비용 | 시세(참고치) | 평형·거리별 편차 |
| A11 | `broker_rate` (one_time) | 0.004 | 중개보수 요율 | 공인중개사법 시행규칙/지자체 고시 | **금액 구간별 상한** — 단일값→구간표는 PART B |
| A12 | `acquisition_rate` (one_time) | 0.011 | 취득세 등 부대비용 요율 | 지방세법 | **가액 구간·감면(생애최초 등)** — PART B |

**Done 기준:** 12개 항목 `checked_at` 채워짐 + 서버 기동 시 "규칙 미검증" 경고 0건(`core/rules.py`가 출력).

---

## PART B. 계산 공식 정밀화 (근사 → 실제 산식)

> 지금은 "곱셈 하나" 수준 근사. 정확도를 올리려면 아래를 구간표/실제 산식으로 교체.
> **영향 파일: `frontend/src/engine/compare.ts` + `backend/app/tools/compare.py` (둘 다) → 동치 테스트 재실행.**

| # | 항목 | 현재 근사 | 정밀화 방향 | 리서치 포인트 |
|---|---|---|---|---|
| B1 | 중개보수 | `deposit × 0.004` 단일 요율 | 거래금액 **구간별 상한요율표** + 임대/매매 구분 | 지자체 고시 요율표를 YAML 테이블로 |
| B2 | 취득세·부대비용 | `price × 0.011` 단일 요율 | 주택가액 **구간별 세율** + 전용면적·다주택·**생애최초 감면** | 지방세법 세율표 + 감면요건 |
| B3 | 전세대출 한도(이사) | `deposit × ltv/(1-ltv)` | 보증기관 **보증한도** + 소득대비 한도 min | HUG/HF 전세보증 한도 규정 |
| B4 | 매매 한도(DSR) | 스트레스금리로 연금현가 1개 | 실제 대출금리 + 스트레스 가산, **원리금 vs 원금균등** 선택 | DSR 산정식(전 대출 합산) — PoC는 단일 대출 가정 |
| B5 | 보증료 월환산 | `deposit × fee_rate ÷ 12` | 주택유형·보증기관별 요율 분기 | 유형 판별 입력이 없으면 "대표값 + 확인 불가" 유지 |
| B6 | 전월세전환 환산 | `monthly × 12 ÷ conv` | 산식 동일하나 `conv`가 기준금리 연동(A2) | 표시 시점 기준금리 반영 |

> ⚠️ B3·B4는 값이 아니라 **공식 구조**를 바꾼다 → `types.ts`/`schemas.py` 응답 필드가 늘어야 하면 **멈추고 사람에게 보고**(헌법). 필드 안 늘리는 선에서 내부 계산만 정밀화 권장.

**Done 기준:** 바꾼 항목에 대해 프론트·백 양쪽 수정 + `pytest`(동치) 통과 + assumptions 행에 근거 문구 갱신.

---

## PART C. 실거래·시세 데이터 (STUB → 실 API)

### C1. 국토부 실거래 (매매·전월세) — 파이프라인 완성, API 호출만 남음
- **채우는 곳:** `backend/app/tools/molit.py::fetch_trades()` 안의 STUB 블록 하나.
  - `PublicDataReader`로 원자료 조회 → **정규화 `TradeRow`**(`{umd_name, price, monthly}`)로 매핑.
  - 필요한 매핑: `법정동→umd_name`, `거래금액/보증금→price(원)`, `월세금→monthly(원)`.
  - 뒤 단계(`aggregate_to_regions`: 동별 중위가·거래건수·예산필터·상위3)는 **완성 + 테스트됨**(`tests/test_molit.py`).
- **리서치 포인트:** 서비스키 발급(공공데이터포털) · 아파트/오피스텔/연립 등 자료 구분 · `sigungu_code`(시군구 코드)·`deal_ymd`(조회 연월) 선택 로직.
- **의존성:** `requirements.txt`의 `PublicDataReader` 주석 해제.

### C2. 시군구 코드 / 조회 대상 동네
- `molit.regions_by_branch()`가 지금은 예시 코드(`11440`=마포)·연월(`202606`) 고정.
- **리서치:** 예산·선호지역 → 후보 시군구 매핑(서울 3~5개 구 우선). 법정동코드 표.

### C3. 좌표·태그 보강 (Enrichment)
- 실거래엔 위경도·태그가 없다 → `aggregate_to_regions(enrich=...)`에 `동→{lat,lng,tags}` 주입.
- **채우는 곳:** enrichment 딕셔너리 소스(지오코딩 API 또는 수기 표). `enrich` 파라미터는 이미 뚫려 있음.

### C4. KB 시세·전세가율 (Optional, 어필 포인트)
- **채우는 곳:** `backend/app/tools/kbland.py::avg_price()` — 지금 `None` 반환.
- KB부동산 데이터허브 평균가·전세가율 → Region/비교표에 병기(매매·전세 격차 표시).
- 실패해도 서비스 진행(Optional).

### C5. 하루 시뮬레이션 데이터 (콘텐츠)
- 지금 `data/catalog.py`의 씬은 고정 fixture(사진 URL·캡션).
- **리서치:** 경로(ODsay/TMAP)·POI(카카오)·물가(참가격)·로드뷰/이미지 → `agents/narrator.py`가 facts 기반 캡션 생성(Phase B4).

**Done 기준:** 실 API 1회 호출 후 `cache/`로 재현 + `GET /api/regions`가 실집계 Region 반환 + 쿼터 보호 확인.

---

## PART D. LLM / RAG 콘텐츠

| # | 항목 | 채우는 곳 | 리서치/작업 |
|---|---|---|---|
| D1 | Claude 실호출 | `core/llm.py::_call_claude` + `.env`(`ANTHROPIC_API_KEY`,`LLM_ENABLED=true`) | 키 발급. **단 verify 재생성 루프(숫자 대조)는 아직 STUB — B4에서 완성 후 켜기** |
| D2 | 상품 RAG 소스 | `backend/data/kb_products/*.md` (5~8건) | 공시 페이지 기준 상품 정리, `source_url` 기재, 숫자는 원문만 인용 |
| D3 | 상품 매칭 | `agents/matcher.py` | md → FAISS → top3 + 사유. `requirements.txt`의 `faiss-cpu` 해제 |
| D4 | 가드레일 문구 | `core/verify.py::SOLICITATION_PATTERNS` | 권유/보험권유 표현 목록 검수(사람 귀로 톤 확인) |

**Done 기준:** briefing 20회 생성에서 facts 외 숫자 0건(verify) + 권유 표현 차단 테스트 통과 + SSE 스트리밍 확인.

---

## 부록 — API 키 발급 목록 (사람이 할 일)
- [ ] 공공데이터포털 — 국토부 실거래 서비스키 → `.env` `MOLIT_API_KEY`
- [ ] Anthropic — Claude API 키 → `.env` `ANTHROPIC_API_KEY`
- [ ] (선택) KB부동산 데이터허브 접근
- [ ] (선택) Langfuse — 트레이싱(Phase B3)
- [ ] (선택) 카카오/ODsay/TMAP/참가격 — 하루 시뮬(Phase B4)
