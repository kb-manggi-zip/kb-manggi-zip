// 백엔드 rules/axis_adjust.yaml 미러 — 방향(닫힌 enum) → 고정 배수. LLM 생성 금지(재현성).
// ⚠️ yaml과 값이 다르면 오프라인/온라인 랭킹이 갈린다. yaml 고치면 여기도 같이.
export type AxisDirection = 'strong_up' | 'up' | 'down' | 'strong_down';

export const DIR_MULT: Record<AxisDirection, number> = {
  strong_up: 1.8,
  up: 1.4,
  down: 0.6,
  strong_down: 0.3,
};
export const AXIS_CLAMP = { min: 0.3, max: 2.0 } as const;

export function dirMult(direction: string): number {
  return DIR_MULT[direction as AxisDirection] ?? 1.0; // 알 수 없는 값 → 변화 없음
}
export function dirSign(direction: string): number {
  return direction === 'up' || direction === 'strong_up' ? 1
    : direction === 'down' || direction === 'strong_down' ? -1 : 0;
}
export const DIRECTIONS = new Set<string>(['strong_up', 'up', 'down', 'strong_down']);
