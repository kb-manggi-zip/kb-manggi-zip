# KB 만기상담소 — 백엔드 API 명세

FastAPI. 기본 `http://localhost:8000`. 모든 요청/응답 `application/json` (UTF-8, 한글 리터럴 유지).

- **API 계약서는 프론트 `frontend/src/api/types.ts`** 이며 백엔드 `app/schemas.py` 와 1:1이다. 필드명·타입·한글 값은 임의 변경 금지.
- LLM 열: `core/llm.py` 의 `settings.llm_active`(키+`LLM_ENABLED`)가 False면 **템플릿/fixture 폴백**으로 동일 스키마 응답.
- 실거래 열: 서버는 외부 API를 호출하지 않고 **SQLite(`data/trades.db` → 없으면 `trades.demo.db`)** 에서 읽는다.

## 엔드포인트 요약

| 메서드 | 경로 | 처리 | LLM | 데이터원 |
|---|---|---|---|---|
| GET | `/health` | 상태 | ❌ | - |
| POST | `/api/compare` | 3갈래 계산 (심장) | ❌ | rules(YAML) |
| GET | `/api/regions` | 동네 후보 3곳 | ❌ | trades DB |
| POST | `/api/simulate` | 하루 씬 | ✅* | catalog fixture |
| POST | `/api/products` | 갈래별 KB 상품 | ✅* | catalog fixture |
| POST | `/api/briefing` | 비교표 통역 문장 | ✅* | templates |
| POST | `/api/draft-notice` | 갱신 통보 문자 초안 | ✅* | template |
| POST | `/api/reservation` | 상담 예약 저장 | ❌ | SQLite |

`*` = 현재 폴백. `POST /api/extract-contract`(계약서 Vision)는 **Phase B5 예정**(미활성).

---

## 공용 타입

**열거형(한글 리터럴)**
- `ContractType`: `"전세" | "월세"`
- `RenewalUsed`: `"미사용" | "사용" | "모름"`
- `Household`: `"1인" | "신혼" | "자녀"`
- `FirstHome`: `"예" | "아니오" | "모름"`
- `Branch`: `"갱신" | "이사" | "매매"`
- `BriefingKind`: `"compare" | "regions" | "renewal" | "revisit" | "dayPlayer" | "savedMoney" | "finance"`

**ContractInfo**
| 필드 | 타입 | 설명 |
|---|---|---|
| `type` | ContractType | 전세/월세 |
| `deposit` | int | 보증금(원) |
| `monthlyRent` | int | 월세(원). 전세는 0 |
| `expiryDate` | string | 만기일 ISO (`YYYY-MM-DD`) |
| `renewalUsed` | RenewalUsed | 갱신청구권 사용 여부 |

**FinanceInfo**
| 필드 | 타입 | 설명 |
|---|---|---|
| `annualIncome` | int | 연소득(원) |
| `ownCapital` | int | 보증금 외 보유자금(원) |
| `household` | Household | 가구형태 |
| `firstHome` | FirstHome | 생애최초 주택구입 여부 |
| `under35` | bool | 만 35세 미만(버팀목 청년 자격) |

**BranchResult**
| 필드 | 타입 | 설명 |
|---|---|---|
| `branch` | Branch | 갈래 |
| `headline` | string | 한 줄 요약 |
| `depositOrPrice` | int | 보증금 또는 집값 상한(원) |
| `loanAmount` | int | 필요 대출(원) |
| `oneTimeCost` | int | 일회성 비용(원) |
| `guaranteeMonthly` | int | 반환보증료 월환산(원) |
| `monthlyBurden` | int | 월 부담(원) |
| `risks` | string[] | 리스크 |
| `cares` | string[] | 대비 |
| `basis` | string[] | 근거 칩 |
| `uncertainty` | string? | 불확실성(있을 때만) |
| `feature` | string | 특징 한마디 |

**Region**
| 필드 | 타입 | 설명 |
|---|---|---|
| `id` | string | 동 식별자 |
| `name` | string | 법정동명 |
| `midPrice` | int | 중위 매매/전세가(원) |
| `monthlyMidPrice` | int? | 월세 중위(원, 월세만) |
| `surplus` | int | 예산 여유(원) = budget − midPrice |
| `tradeCount` | int | 최근 거래 건수 |
| `tags` | string[] | 태그(역세권 등) |
| `lat` / `lng` | float | 좌표 |
| `branch` | Branch | 이사/매매 |

**Scene** `{ time, emoji, visual(url), caption1, caption2, basis? }`
**Product** `{ name, condition, recommendReason, monthlyPayment?, maxAmount?, basis }`

---

## GET /health
상태 확인. LLM 활성 여부·DB 종류 노출.
```json
{ "status": "ok", "llm_active": false, "db": "sqlite" }
```

## POST /api/compare  ★ 심장
세 갈래를 계산해 비교표를 반환. LLM 미사용(전부 결정론적). 매매는 **수도권 규제지역 가정**.

**요청** `CompareRequest`
```json
{
  "contract": { "type": "전세", "deposit": 320000000, "monthlyRent": 0,
                "expiryDate": "2026-10-30", "renewalUsed": "미사용" },
  "finance":  { "annualIncome": 80000000, "ownCapital": 60000000,
                "household": "신혼", "firstHome": "예", "under35": true }
}
```

**응답** `CompareResponse`
| 필드 | 타입 | 설명 |
|---|---|---|
| `branches` | BranchResult[] | 순서 = [갱신, 이사, 매매] |
| `dday` | int | 만기까지 남은 일수 |
| `noticeDaysLeft` | int | 갱신 통보기한까지 |
| `noticeDeadline` | string | 통보기한(`YYYY-MM-DD`) |
| `monthlyToDeposit` | int | 월세→보증금 환산(월세만) |
| `savings` | int | 갱신 시 아끼는 일회성 비용 |
| `assumptions` | string[] | 계산 가정(근거) |

```jsonc
{ "branches": [
    { "branch": "갱신", "headline": "보증금 3억 3,600만으로 그대로",
      "depositOrPrice": 336000000, "loanAmount": 16000000, "oneTimeCost": 0,
      "guaranteeMonthly": 40400, "monthlyBurden": 84400,
      "risks": ["보증금 반환 위험 지속", "임대인 사정에 따라 거절 가능"],
      "cares": ["반환보증 점검 (+4만/월)", "계약서 특약 확인"],
      "basis": ["법정 상한 5%", "HUG 공시 요율"], "feature": "가장 가볍고 익숙함" },
    { "branch": "이사", "headline": "새 전세 최대 5억 4,200만", "...": "..." },
    { "branch": "매매", "headline": "최대 7억 7,681만 내 집", "depositOrPrice": 776806525,
      "loanAmount": 396806525, "monthlyBurden": 1694512, "guaranteeMonthly": 0,
      "basis": ["규제지역 LTV 70%", "KB 한도 3억", "스트레스 DSR 가산 3.0%", "디딤돌 혼합"],
      "...": "..." }
  ],
  "dday": 103, "noticeDaysLeft": 42, "noticeDeadline": "2026-08-30",
  "monthlyToDeposit": 0, "savings": 2780000,
  "assumptions": ["전세대출 금리 KB 3.89% (HF 공시)", "규제지역 LTV 40% (생애최초 70%)",
                  "KB 주택구입 대출 한도 3억 (2026.7~)", "스트레스 DSR 수도권 3.0% (한도 산정에만 적용)",
                  "보증료 HUG 공시 요율 (아파트·부채비율 80% 이하 가정)",
                  "기존 대출이 없다고 가정했어요. 대출이 있으면 한도가 줄어들 수 있어요", "법정 상한 5%"] }
```
> `firstHome`이 `"모름"`이면 매매에 `uncertainty`가 붙고 assumptions에 "생애최초라면 LTV 70%까지…"가 추가된다.

## GET /api/regions
예산 이내 동네 후보 상위 3곳(거래 활발 순). **실거래 DB** 집계.

**쿼리**: `branch` = `매매`|`이사`|`이사-월세`, `budget` = int(원)
```
GET /api/regions?branch=매매&budget=600000000
```
**응답** `Region[]`
```json
[ { "id": "mapo", "name": "합정동", "midPrice": 524959796, "surplus": 75040204,
    "tradeCount": 240, "tags": ["역세권","카페거리"], "lat": 37.5498, "lng": 126.9137,
    "branch": "매매", "monthlyMidPrice": null } ]
```
> **에러**: DB가 비어있으면 `500` + "refresh_deals.py 를 먼저 실행하세요". 데모는 `trades.demo.db` 커밋으로 항상 응답.

## POST /api/simulate
선택 갈래×동네의 "하루" 씬. 현재 fixture(narrator seam).
**요청** `{ "branch": "매매", "regionId": "mapo" }` → **응답** `{ "scenes": Scene[5], "monthlyCost": int }`

## POST /api/products
갈래별 KB "대출+보장" 패키지. 현재 fixture(matcher/RAG seam). 권유 표현 금지.
**요청** `{ "branch": "매매", "comparison": CompareResponse? }`
**응답** `ProductsResponse` `{ branch, mainLoan: Product, guarantee?: Product, extra?: Product }`

## POST /api/briefing
비교표/화면을 읽어주는 통역 문장(한 번에 반환). LLM 폴백=템플릿(`agents/templates.py`).
**요청** `{ "kind": "compare", "context": { "comparison": CompareResponse, "name": "신혼 가구" } }`
**응답** `{ "text": "..." }`

## POST /api/briefing/stream  (SSE)
같은 입력을 **토큰 단위로 스트리밍**(`text/event-stream`) — 프론트 타이핑 UX와 연결.
- `llm_active=True`: Claude `messages.stream()` 델타. `False`: 폴백 템플릿을 어절 단위로.
- 이벤트: `data: <청크>` 반복 → `event: done` / `data: [DONE]` 로 종료.
- 프론트: `api.streamBriefing(req, onChunk, localText)` (원격=SSE, 로컬=어절 시뮬레이션), `AiBriefing`이 `live` 모드로 점진 렌더.
```
data: 신혼 가구님,
data:  세 경우를 계산했어요...
event: done
data: [DONE]
```

## POST /api/draft-notice
갱신 의사 통보 문자 초안. 법적 확언·권유 금지, 빈 항목은 `[대괄호]` placeholder.
**요청** `{ "expiryDate": "2026-10-30", "address": "마포구 ..." }` → **응답** `{ "draft": "안녕하세요, ..." }`

## POST /api/reservation
상담 예약 저장(SQLite/Postgres).
**요청** `{ "branch": "매매", "date": "2026-08-01", "productName": "KB 주담대" }`
**응답** `{ "ok": true, "id": 1 }`

---

## 오류 규약
- `422` — 요청 스키마 불일치(Pydantic 검증).
- `500` — 실거래 DB 미준비 등(메시지에 조치 안내 포함).
- LLM 호출 실패는 조용히 삼키지 않고 로깅 후 **템플릿 폴백**(서비스 지속).

## 계약 변경 규칙
`schemas.py` / `types.ts` 를 바꿔야 풀리는 문제는 **중단하고 사람에게 보고**한다(루트 `CLAUDE.md` 헌법). 프론트·백 양쪽을 함께 고치고 동치 테스트를 재실행한다.
