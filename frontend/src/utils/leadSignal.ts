import type { PersonaProfile } from '../api/types';

// L3/하루시뮬 공용 — 확정 신호만(실측>진술>세그먼트), 같은 출처 안에서는 "많이 하는" 신호를 우선.
// "적게 하는" 신호를 먼저 뽑아 "많이 하는"(실제로 보여줄 수 있는) 신호를 가리던 문제 방지(2026-07-31).
export function deriveLeadSignal(signals: PersonaProfile['consumptionSignals']): string | undefined {
  const sig = signals ?? [];
  const pickFrom = (source: string) => {
    const inSource = sig.filter((s) => s.source === source);
    return inSource.find((s) => s.label.includes('많이 하는')) ?? inSource[0];
  };
  const pick = pickFrom('실측') ?? pickFrom('진술') ?? pickFrom('세그먼트');
  return pick?.label;
}
