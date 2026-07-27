import React, { useEffect, useState } from 'react';
import { useApp } from '../store';
import { COLORS } from '../theme';
import { MobileShell, PrimaryBtn } from '../components/ui';
import { formatAmount } from '../utils/format';
import { api } from '../api/client';
import type { PersonaProfile } from '../api/types';

const AXIS: Record<string, string> = { commute: '통근', consumption: '생활·소비', budget: '예산', preference: '선호지역' };

// 문진 완료 직후 1회 — 풀스크린 '당신의 프로필'. [이대로 비교하기]로 비교표(SC-03)로.
export default function ProfileConfirm() {
  const { state, dispatch } = useApp();
  const { contract, finance } = state;
  const [persona, setPersona] = useState<PersonaProfile | null>(null);

  useEffect(() => {
    if (!contract || !finance) { dispatch({ type: 'NAVIGATE', screen: 'SC-03' }); return; }
    api.persona(contract, finance).then(setPersona).catch(() => setPersona(null));
  }, [contract, finance]);

  if (!contract || !finance) return null;

  const facts: [string, string][] = [
    ['계약', contract.type],
    ['보증금', formatAmount(contract.deposit)],
    ['소득', formatAmount(finance.annualIncome)],
    ['자본', formatAmount(finance.ownCapital)],
    ['가구', finance.household],
  ];
  const weights = persona ? Object.entries(persona.weights).sort((a, b) => b[1] - a[1]) : [];

  return (
    <MobileShell>
      <div className="flex-1 overflow-y-auto px-5 py-6 space-y-4">
        <div className="text-center pt-2">
          <p className="text-2xl">🎯</p>
          <h1 className="text-xl font-bold mt-2" style={{ color: COLORS.KB_GRAY }}>당신의 프로필</h1>
          <p className="text-sm text-muted-foreground mt-1">{persona?.headline ?? '프로필을 정리하고 있어요…'}</p>
        </div>

        {/* 사실 */}
        <div className="rounded-2xl border border-border p-4">
          <p className="text-xs font-semibold mb-2" style={{ color: COLORS.SUB }}>사실 (문진 입력)</p>
          <div className="grid grid-cols-2 gap-y-2 gap-x-3">
            {facts.map(([k, v]) => (
              <div key={k} className="flex justify-between text-sm">
                <span className="text-muted-foreground">{k}</span><span className="font-semibold">{v}</span>
              </div>
            ))}
          </div>
        </div>

        {/* 우선순위 가중치 */}
        {persona && (
          <div className="rounded-2xl border border-border p-4 space-y-1.5">
            <p className="text-xs font-semibold mb-1" style={{ color: COLORS.SUB }}>동네를 볼 때 중요하게 여기는 순서</p>
            {weights.map(([k, v]) => (
              <div key={k} className="flex items-center gap-2">
                <span className="text-xs w-14 shrink-0 text-muted-foreground">{AXIS[k] ?? k}</span>
                <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: '#0000000d' }}>
                  <div className="h-full rounded-full" style={{ width: `${Math.round(v * 100)}%`, background: COLORS.KB_YELLOW }} />
                </div>
                <span className="text-xs w-9 text-right tabular-nums text-muted-foreground">{Math.round(v * 100)}%</span>
              </div>
            ))}
            <p className="text-[11px] pt-1" style={{ color: COLORS.SUB }}>근거: {persona.weightBasis}</p>
          </div>
        )}

        {/* 성향 신호 */}
        {persona && (persona.consumptionSignals?.length ?? 0) > 0 && (
          <div className="rounded-2xl border border-border p-4">
            <p className="text-xs font-semibold mb-2" style={{ color: COLORS.SUB }}>성향</p>
            <div className="flex flex-wrap gap-1.5">
              {persona.consumptionSignals!.map((s, i) => (
                <span key={i} title={s.reason} className="text-[11px] px-2 py-0.5 rounded-full"
                  style={s.source === '실측' ? { border: `1px solid ${COLORS.KB_YELLOW}`, color: COLORS.TEXT, fontWeight: 600 } : { background: '#00000008', color: COLORS.SUB }}>
                  {s.source === '실측' ? '실측 ' : ''}{s.label}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="px-5 pb-8 pt-2 space-y-2">
        <PrimaryBtn onClick={() => dispatch({ type: 'NAVIGATE', screen: 'SC-03' })}>이대로 비교하기</PrimaryBtn>
        <button onClick={() => dispatch({ type: 'NAVIGATE', screen: 'SC-02' })}
          className="w-full py-2.5 rounded-xl text-sm font-semibold border" style={{ borderColor: COLORS.BORDER, color: COLORS.SUB }}>
          문진 수정하기
        </button>
      </div>
    </MobileShell>
  );
}
