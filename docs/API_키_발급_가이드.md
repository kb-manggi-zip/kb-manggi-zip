# API 키 발급 & 연결 가이드 (사람이 할 일)

> 모든 키는 `backend/.env`에 넣는다(gitignore됨, 절대 커밋 금지). 서버 런타임은 외부 API를 직접 안 친다 —
> **수집은 `scripts/refresh/`(오프라인)에서만**, 런타임은 DB/폴백만 읽음. 키 없어도 앱은 폴백으로 동작.

## 한눈에
| 키 | 무엇 | .env 변수 | 쓰는 곳 | 없으면 |
|---|---|---|---|---|
| MOLIT | 국토부 실거래 | `MOLIT_API_KEY` | `refresh_deals.py` | 커밋된 trades.demo.db 사용 |
| SBIZ | 소상공인 상권 | `SBIZ_API_KEY` | `refresh_regions.py` | 상권 발품 생략(이름+태그) |
| ODsay | 대중교통 통근시간 | `ODSAY_API_KEY` | `tools/transit.py` | 직선거리 **예상치**(조건부 서술) |
| Anthropic | LLM(발품·통역) | `ANTHROPIC_API_KEY` | `core/llm.py` | 템플릿 폴백 |
| Langfuse | 관측성 | `LANGFUSE_*` | `core/tracing.py` | 트레이싱 비활성 |

---

## 1. SBIZ — 소상공인 상권정보 (상권 발품)
1. **공공데이터포털** [data.go.kr](https://www.data.go.kr) 로그인.
2. 검색: **"소상공인시장진흥공단_상가(상권)정보"** → 오픈API 활용신청(자동승인).
3. 마이페이지 → 개발계정 → **일반 인증키(Decoding)** 복사. ⚠️ Encoding 말고 **Decoding**.
4. `backend/.env`에: `SBIZ_API_KEY=<Decoding 키>`
5. 실행:
   ```bash
   cd backend && source .venv/bin/activate
   python scripts/refresh/refresh_regions.py inspect   # 실 응답 키 확인
   TRADES_DB=data/trades.demo.db python scripts/refresh/refresh_regions.py   # 9개 동 수집
   git add data/trades.demo.db   # 스냅샷 커밋
   ```

## 2. ODsay — 대중교통 길찾기 (통근시간 발품)
1. **[lab.odsay.com](https://lab.odsay.com)** 가입 → 로그인.
2. 마이페이지 → **애플리케이션 등록** → 웹서비스 → 생성.
3. 발급된 **API Key** 복사. (무료 일 1,000회 등 한도 있음)
4. `backend/.env`에: `ODSAY_API_KEY=<키>`
5. 검증 (실 응답 형식 확인 — 코드가 공개스펙 기준이라 1회 확인 권장):
   ```bash
   cd backend && source .venv/bin/activate
   python -c "from app.tools import transit; print(transit.commute(37.5561,126.9026,37.5219,126.9245))"
   # estimated:False + minutes 나오면 실측 정상. False가 아니면 키/응답 확인.
   ```
   → 발품에 "여의도로 통근한다면 약 N분"이 **예상 아닌 실측**으로 바뀜.

## 3. TMAP (선택 — ODsay 대안/보완)
- 현재 코드는 **ODsay를 사용**. TMAP은 자동차 경로·대중교통 대안으로 붙일 수 있음(필수 아님).
1. **[openapi.sk.com](https://openapi.sk.com)** (SK open API) 가입 → TMAP API 이용신청.
2. 앱 등록 → **appKey** 발급 → `.env` `TMAP_API_KEY=<키>`.
3. 붙이려면: `tools/transit.py`에 TMAP 분기 추가(`/tmap/routes` 자동차, `/transit/routes` 대중교통). ODsay 실패 시 TMAP 폴백 등.
   - ⚠️ 미구현(seam만). 필요 시 요청.

## 4. (이미 있음) MOLIT · Anthropic · Langfuse
- **MOLIT**: 공공데이터포털 "국토교통부_아파트/연립다세대 실거래가" 활용신청 → `MOLIT_API_KEY`. `refresh_deals.py`로 재수집.
- **Anthropic**: [console.anthropic.com](https://console.anthropic.com) → API Key → `ANTHROPIC_API_KEY` (+ `LLM_ENABLED=true`).
- **Langfuse**: [cloud.langfuse.com](https://cloud.langfuse.com) → 프로젝트 → `LANGFUSE_PUBLIC_KEY`·`LANGFUSE_SECRET_KEY`.

---
## 원칙
- 키는 `.env`에만. **코드·커밋·로그·채팅에 노출 금지.** (`.env.example`만 커밋)
- 수집은 오프라인 스크립트, 런타임은 DB/폴백. 데모는 스냅샷으로 네트워크 없이 완주.
