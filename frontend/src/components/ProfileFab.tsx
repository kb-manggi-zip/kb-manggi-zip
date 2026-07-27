import React, { useEffect, useState } from 'react';
import { useApp } from '../store';
import { COLORS } from '../theme';
import { api } from '../api/client';
import { formatAmount } from '../utils/format';
import type { PersonaProfile } from '../api/types';

// 어느 화면에서든 '당신의 프로필'을 바텀시트로 열람(상시 조회). 편집은 문진으로 돌아가기 링크만.
export default function ProfileFab() {
  const { state, dispatch } = useApp();
  const { contract, finance } = state;
  const [open, setOpen] = useState(false);
  const [persona, setPersona] = useState<PersonaProfile | null>(null);

  useEffect(() => {
    if (!open || !contract || !finance) return;
    api.persona(contract, finance).then(setPersona).catch(() => setPersona(null));
  }, [open, contract, finance]);

  if (!contract || !finance) return null; // 문진 전엔 표시 안 함

  const facts: [string, string][] = [
    ['계약', `${contract.type}${contract.housingType ? ` · ${contract.housingType === '아파트' ? '아파트' : '연립·다세대'}` : ''}`],
    ['보증금', formatAmount(contract.deposit)],
    ...(contract.type === '월세' ? [['월세', formatAmount(contract.monthlyRent)] as [string, string]] : []),
    ['소득', formatAmount(finance.annualIncome)],
    ['자본', formatAmount(finance.ownCapital)],
    ['가구', finance.household],
  ];

  return (
    <>
      {/* 상단 우측 프로필 아이콘 */}
      <button
        onClick={() => setOpen(true)}
        aria-label="내 프로필"
        className="absolute top-2 right-3 z-40 w-8 h-8 rounded-full flex items-center justify-center text-sm"
        style={{ background: COLORS.KB_YELLOW, color: COLORS.TEXT, boxShadow: '0 2px 6px rgba(0,0,0,0.15)' }}
      >
        👤
      </button>

      {open && (
        <div className="absolute inset-0 z-50 flex flex-col justify-end" style={{ background: 'rgba(0,0,0,0.35)' }} onClick={() => setOpen(false)}>
          <div className="bg-card rounded-t-3xl p-5 space-y-4 max-h-[80%] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold" style={{ color: COLORS.TEXT }}>당신의 프로필</h2>
              <button onClick={() => setOpen(false)} className="text-muted-foreground text-lg">✕</button>
            </div>

            {/* 사실 카드 */}
            <div className="rounded-2xl border border-border p-4">
              <p className="text-xs font-semibold mb-2" style={{ color: COLORS.SUB }}>사실 (문진 입력)</p>
              <div className="grid grid-cols-2 gap-y-2 gap-x-3">
                {facts.map(([k, v]) => (
                  <div key={k} className="flex justify-between text-sm">
                    <span className="text-muted-foreground">{k}</span>
                    <span className="font-semibold">{v}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* 성향 칩 (실측 배지 구분) */}
            {persona && (persona.consumptionSignals?.length ?? 0) > 0 && (
              <div className="rounded-2xl border border-border p-4 space-y-2">
                <p className="text-xs font-semibold" style={{ color: COLORS.SUB }}>성향</p>
                <div className="flex flex-wrap gap-1.5">
                  {persona.consumptionSignals!.map((s, i) => (
                    <span key={i} title={s.reason}
                      className="text-[11px] px-2 py-0.5 rounded-full"
                      style={s.source === '실측'
                        ? { border: `1px solid ${COLORS.KB_YELLOW}`, color: COLORS.TEXT, fontWeight: 600 }
                        : { background: '#00000008', color: COLORS.SUB }}>
                      {s.source === '실측' ? '실측 ' : ''}{s.label}
                    </span>
                  ))}
                </div>
                <p className="text-[11px] leading-snug" style={{ color: COLORS.SUB }}>
                  '실측' 배지는 시연용 합성 데이터 기준이에요. 실서비스에서는 마이데이터 동의 후 실제 내역으로 분석됩니다.
                </p>
              </div>
            )}

            <button
              onClick={() => { setOpen(false); dispatch({ type: 'NAVIGATE', screen: 'SC-02' }); }}
              className="w-full py-2.5 rounded-xl text-sm font-semibold border"
              style={{ borderColor: COLORS.BORDER, color: COLORS.SUB }}
            >
              문진으로 돌아가 수정하기
            </button>
          </div>
        </div>
      )}
    </>
  );
}
