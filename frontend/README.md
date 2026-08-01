# KB만기.zip — 프론트엔드

전월세 만기 D-90, **세 갈래(갱신·이사·매매)** 비교 화면. React 18 + Vite 6 + TypeScript + Tailwind v4.
모바일(max-width 390) 단일 흐름. Figma Make에서 생성.

## 실행

```bash
cd frontend
npm i          # 최초 1회 (lockfile 없음 — npm 사용)
npm run dev    # http://localhost:5173
npm run build  # 프로덕션 정적 빌드 (dist/) — 타입체크 겸용
```

## 두 가지 실행 모드 ★ (백엔드 없이도 돈다)

프론트는 **혼자서도 완전히 동작**한다. 백엔드 연결은 선택이다.

| 모드 | 설정 | 계산 주체 | 용도 |
|---|---|---|---|
| **로컬 모드** | `VITE_API_URL` 없음 (기본) | 브라우저 안의 `src/engine`·`src/data` | 데모 백업, 오프라인 시연 |
| **에이전트 모드** | `VITE_API_URL` 설정 | `backend`(FastAPI) 호출 | 실데이터·LLM 통역 |

전환은 환경변수 하나. `src/api/client.ts`의 `localOrRemote()`가 분기한다 — **화면 코드는 무수정.**

```bash
# frontend/.env  (에이전트 모드로 켜려면)
VITE_API_URL=http://localhost:8000
```

### "백엔드·프론트 둘 다 켜야 하나?"
- **로컬 모드: 프론트 하나만** 실행하면 끝 (`npm run dev`). 백엔드 불필요.
- **에이전트 모드: 둘 다.** 터미널 2개 —
  ```bash
  # 터미널 1 — 백엔드
  cd backend && source .venv/bin/activate && uvicorn app.main:app --reload
  # 터미널 2 — 프론트 (frontend/.env에 VITE_API_URL 설정 후)
  cd frontend && npm run dev
  ```
  또는 백엔드를 도커로: 루트에서 `docker compose up --build` (프론트만 `npm run dev`).
- **배포**: 프론트는 정적(`dist/` → Vercel), 백엔드는 별도(Railway). 서로 다른 서비스로 각각 배포된다.

## 구조 (요점만)
- `src/api/types.ts` — **백엔드와의 API 계약서** (백엔드 `schemas.py`와 1:1). 함부로 바꾸지 않는다.
- `src/api/client.ts` — 로컬/원격 seam. 화면은 항상 이걸 경유(엔진·데이터 직접 import 금지).
- `src/engine/compare.ts` — 3갈래 계산의 **참조 구현**. 백엔드 `tools/compare.py`가 이 출력과 오차 0으로 일치.
- `src/engine/rules.ts` — 규정 수치(예시값). 백엔드는 `rules/*.yaml`. **둘을 함께 바꿔야 한다** (아래).
- `src/store.tsx` + `src/app/App.tsx` — `SC-01`~`SC-12` 화면 상태 흐름(스위치 라우터, URL 라우팅 아님).

> ⚠️ 계산 공식이나 규정 수치를 바꾸려면 **프론트(`engine/`)와 백엔드(`tools/`·`rules/`) 양쪽**을 같이 고치고
> `backend`에서 동치 테스트를 다시 돌려야 한다. 리서치 대상은 루트 `RESEARCH.md` 참고.
