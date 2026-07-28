# 배포 가이드 — 프론트 Vercel + 백엔드 Render (무료)

구조: **프론트(Vercel 정적) → `VITE_API_URL`로 백엔드(Render) 호출.** 백엔드가 살아있어야
AI 검증·동네 스코어·발품·지출·다음액션이 모두 동작한다(없으면 프론트만 로컬 폴백으로 계산만).

> ⚠️ 두 서비스는 서로의 주소를 알아야 해서 **순서상 백엔드를 먼저** 올리고, 그 주소를 프론트에 넣는다.

---

## 1) 백엔드 — Render

1. [render.com](https://render.com) 로그인 → **New +** → **Blueprint** → 이 GitHub 레포 선택.
   - 루트의 `render.yaml`을 자동 인식 (`kb-manggi-api`, root `backend`, `requirements-runtime.txt`로 빌드).
2. 배포 중 **Environment**에 secret 입력:
   - `ANTHROPIC_API_KEY` = (Anthropic 콘솔 키) — **레포에 넣지 말 것.**
   - `CORS_ORIGINS` = 프론트 Vercel 주소 (2단계에서 확정. 처음엔 임시로 `*` 넣고 나중에 교체 가능하나 시연 전엔 실제 주소로).
   - (`LLM_ENABLED=true`는 render.yaml에 이미 있음)
3. 배포 완료 후 주소 확인: `https://kb-manggi-api.onrender.com`
   - 헬스체크: `https://kb-manggi-api.onrender.com/health` → `{"status":"ok","llm_active":true,...}` 나오면 AI 라이브.
   - `llm_active:false`면 키 미설정 → 폴백 모드(문제는 아니지만 AI 미노출).

## 2) 프론트 — Vercel

1. [vercel.com](https://vercel.com) → **Add New** → **Project** → 이 레포 선택.
2. **Root Directory = `frontend`** 로 설정 (중요). 프레임워크는 Vite 자동 인식(`frontend/vercel.json`).
3. **Environment Variables**:
   - `VITE_API_URL` = `https://kb-manggi-api.onrender.com` (1단계 백엔드 주소, 끝에 슬래시 없이)
4. Deploy → 주소 확인: `https://<프로젝트>.vercel.app`

## 3) 연결 마무리

- Render의 `CORS_ORIGINS`를 2단계에서 나온 **실제 Vercel 주소**로 교체 → 저장(자동 재배포).
- 프론트에서 문진→계산→동네→발품→리포트까지 눌러보며 백엔드 응답 확인.

---

## 무료 콜드스타트 대비 (심사·시연용)

Render 무료 web service는 **15분 미사용 시 잠들었다가 다음 요청에 ~30-60초** 걸린다.
심사 기간엔 [UptimeRobot](https://uptimerobot.com)(무료)에서 **5분 간격 HTTP 모니터**로
`https://kb-manggi-api.onrender.com/health` 를 핑하면 깨어있게 유지된다.

- 항상 켜두고 싶으면 Render 유료(Starter, 월 $7) 전환 = 클릭 한 번.
- **라이브 프레젠테이션**은 백엔드를 로컬(`uvicorn app.main:app`)로 띄워 콜드스타트 없이 시연하고,
  배포 링크는 "직접 눌러보는 제출용"으로 두는 것도 방법.

## 로컬에서 프론트가 배포 백엔드를 바라보게 테스트

```bash
cd frontend
VITE_API_URL=https://kb-manggi-api.onrender.com npm run dev
```

## 참고
- 배포 백엔드는 SQLite 임시 파일 → **예약 등 쓰기 데이터는 재배포 시 초기화**(데모엔 무해).
  영속 필요 시 Render Postgres(무료) 연결 후 `DATABASE_URL` 환경변수 추가.
- 실거래/상권 데이터(`backend/data/*.demo.db`)는 레포에 포함돼 함께 배포된다(읽기 전용).
