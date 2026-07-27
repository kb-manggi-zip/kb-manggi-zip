import React, { useEffect, useState } from 'react';
import { useApp } from '../store';
import { COLORS } from '../theme';
import { MobileShell, PrimaryBtn, DdayBar } from '../components/ui';
import { formatAmount } from '../utils/format';
import { api } from '../api/client';
import type { PersonaProfile } from '../api/types';

function householdLabel(h: string) {
  return h === '1인' ? '1인 가구' : h === '신혼' ? '신혼 가구' : '자녀 가구';
}

// 문진 완료 직후 1회 — '당신의 프로필'. 확실한 것만: 사실 + 칩(사실 파생·본인 진술·실측). 가중치 바·세그먼트 통계 칩 없음.
export default function ProfileConfirm() {
  const { state, dispatch } = useApp();
  const { contract, finance, comparison } = state;
  const [persona, setPersona] = useState<PersonaProfile | null>(null);
  const [conflicts, setConflicts] = useState<string[]>([]);
  const [tooltip, setTooltip] = useState<string | null>(null);

  useEffect(() => {
    if (!contract || !finance) { dispatch({ type: 'NAVIGATE', screen: 'SC-03' }); return; }
    api.persona(contract, finance).then(setPersona).catch(() => setPersona(null));
    // 최종 확인: 합쳐진 자유입력에 상충이 남아있으면 되묻는다(조용한 반영 금지).
    api.clarify(contract, finance).then(r => setConflicts(r.conflicts ?? [])).catch(() => setConflicts([]));
  }, [contract, finance]);

  if (!contract || !finance) return null;

  const signals = persona?.consumptionSignals ?? [];
  const measured = signals.filter(s => s.source === '실측');
  const stated = signals.filter(s => s.source === '진술');

  return (
    <MobileShell>
      {comparison && <DdayBar dday={comparison.dday} noticeDaysLeft={comparison.noticeDaysLeft} />}

      <div className="flex items-center gap-2 px-5 py-3">
        <button onClick={() => dispatch({ type: 'NAVIGATE', screen: 'SC-02' })} className="text-muted-foreground text-lg -ml-1 p-2">←</button>
        <span className="text-sm text-muted-foreground">비교 전 확인</span>
      </div>

      <div className="flex-1 overflow-y-auto px-5 pb-8 space-y-5">
        <h1 className="text-2xl font-bold" style={{ color: COLORS.KB_GRAY }}>당신의 프로필</h1>

        {/* 상충 재확인 — 합쳐진 자유입력에 모순이 남아있으면 정정 유도 */}
        {conflicts.length > 0 && (
          <div className="rounded-2xl p-4 space-y-2" style={{ background: COLORS.YELLOW_SURFACE, border: `1px solid ${COLORS.KB_YELLOW}` }}>
            <p className="text-sm font-bold" style={{ color: COLORS.KB_GRAY }}>⚠️ 입력에 상충이 남아있어요</p>
            {conflicts.map((c, i) => <p key={i} className="text-xs" style={{ color: COLORS.SUB }}>· {c}</p>)}
            <button onClick={() => dispatch({ type: 'NAVIGATE', screen: 'SC-02' })}
              className="w-full mt-1 py-2 rounded-xl text-xs font-semibold" style={{ background: COLORS.KB_YELLOW, color: COLORS.TEXT }}>
              문진에서 정정하기
            </button>
          </div>
        )}

        {/* 사실 섹션 */}
        <div className="bg-card rounded-3xl border border-border overflow-hidden" style={{ boxShadow: '0 2px 12px rgba(0,0,0,0.07)' }}>
          <div className="px-5 py-3 text-xs font-bold uppercase tracking-widest" style={{ background: COLORS.KB_YELLOW + '30', color: COLORS.KB_GRAY }}>사실</div>
          <div className="px-5 py-4 space-y-3">
            <FactRow label="계약 유형" value={contract.type} />
            <FactRow label="보증금" value={formatAmount(contract.deposit)} />
            {contract.monthlyRent > 0 && <FactRow label="월세" value={`${Math.round(contract.monthlyRent / 10_000)}만원/월`} />}
            <FactRow label="연소득" value={formatAmount(finance.annualIncome)} />
            <FactRow label="보유 자본" value={formatAmount(finance.ownCapital)} />
            <FactRow label="가구 형태" value={householdLabel(finance.household)} />
          </div>
        </div>

        {/* 성향 태그 — 사실 파생 + 본인 진술 + 실측(배지) */}
        <div className="space-y-3">
          <p className="text-sm font-semibold text-muted-foreground px-1">성향</p>
          <div className="flex flex-wrap gap-2">
            {/* 사실 파생(단정 아님) */}
            <FactTag label={householdLabel(finance.household)} />
            <FactTag label={contract.type === '전세' ? '전세 거주 중' : '월세 거주 중'} />
            {finance.firstHome !== '아니오' && <FactTag label="생애최초 가능 검토" />}
            <FactTag label={finance.annualIncome >= 70_000_000 ? '소득 안정' : '소득 성장 단계'} />
            {/* 본인 진술(확정한 조정) */}
            {stated.map((s, i) => <FactTag key={`st${i}`} label={s.label} note="직접 말씀하신 내용" />)}
            {/* 실측(합성) — 배지 + 근거 툴팁 */}
            {measured.map((s, i) => (
              <button key={`m${i}`}
                onClick={() => setTooltip(tooltip === s.reason ? null : (s.reason ?? null))}
                className="flex items-center gap-1.5 px-3 py-2 rounded-full border text-sm font-medium transition-all active:scale-95"
                style={{ borderColor: COLORS.KB_YELLOW, background: COLORS.YELLOW_SURFACE, color: COLORS.KB_GRAY }}>
                {s.label}
                <span className="text-xs px-1.5 py-0.5 rounded-full font-bold" style={{ background: COLORS.KB_YELLOW, color: COLORS.TEXT }}>실측</span>
              </button>
            ))}
          </div>

          {tooltip && (
            <div className="px-4 py-3 rounded-2xl text-sm" style={{ background: COLORS.YELLOW_SURFACE, borderLeft: `3px solid ${COLORS.KB_YELLOW}` }}>
              <p className="text-foreground/80 leading-relaxed">{tooltip}</p>
              <p className="text-xs text-muted-foreground mt-1">탭하면 닫혀요</p>
            </div>
          )}
        </div>

        <div className="px-4 py-3 rounded-2xl text-xs text-muted-foreground" style={{ background: COLORS.BORDER + '60' }}>
          🔒 "실측" 배지는 시연용 합성 데이터예요. 실서비스는 마이데이터 동의 후 실제 내역을 분석해요.
        </div>
      </div>

      <div className="px-5 pb-8 pt-3">
        <PrimaryBtn onClick={() => dispatch({ type: 'NAVIGATE', screen: 'SC-03' })}>이대로 비교하기 →</PrimaryBtn>
      </div>
    </MobileShell>
  );
}

function FactRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between py-1 border-b border-border/50 last:border-0">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-sm font-semibold text-foreground">{value}</span>
    </div>
  );
}

function FactTag({ label, note }: { label: string; note?: string }) {
  return (
    <span title={note} className="px-3 py-2 rounded-full border text-sm font-medium"
      style={{ borderColor: COLORS.BORDER, background: COLORS.CARD, color: COLORS.KB_GRAY }}>
      {label}
    </span>
  );
}
