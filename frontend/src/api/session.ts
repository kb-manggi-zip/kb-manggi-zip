// 사용자 여정(journey) 식별자 — 백엔드에 X-Session-Id 헤더로 전달되어
// Langfuse Sessions에서 analyze→regions→simulate→products 호출이 한 여정으로 묶인다.
// 스키마(body) 변경 없이 헤더로만 전달(계약 불변).

const KEY = 'kb_session_id';

function uuid(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) return crypto.randomUUID();
  // 폴백(구형 환경): 충돌 가능성 낮은 임의 문자열
  return `s-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

/** 현재 여정 세션ID(없으면 생성해 유지). */
export function getSessionId(): string {
  let id = localStorage.getItem(KEY);
  if (!id) {
    id = uuid();
    localStorage.setItem(KEY, id);
  }
  return id;
}

/** 새 여정 시작(홈으로 리셋 등) — 새 세션ID 발급. */
export function newSession(): string {
  const id = uuid();
  localStorage.setItem(KEY, id);
  return id;
}
