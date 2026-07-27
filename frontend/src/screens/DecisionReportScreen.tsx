import React, { useEffect, useState } from 'react';
import { useApp } from '../store';
import { COLORS, BRANCH_COLORS, BRANCH_ICONS } from '../theme';
import { MobileShell, BackBtn, PrimaryBtn, Disclaimer } from '../components/ui';
import { formatAmount } from '../utils/format';
import { api } from '../api/client';
import type { DecisionReport } from '../api/types';

const man = (won: number) => `${Math.round(won / 10_000).toLocaleString()}만원`;

// 리포트 섹션 카드 — 번호 + 제목 + 내용
function Section({ n, title, children }: { n: string; title: string; children: React.ReactNode }) {
  return (
    <div className="bg-card rounded-2xl border border-border p-4 space-y-2">
      <div className="flex items-center gap-2">
        <span className="text-xs font-bold w-5 h-5 rounded-full flex items-center justify-center"
          style={{ background: COLORS.KB_YELLOW, color: COLORS.TEXT }}>{n}</span>
        <h2 className="text-sm font-bold" style={{ color: COLORS.TEXT }}>{title}</h2>
      </div>
      {children}
    </div>
  );
}

export default function DecisionReportScreen() {
  const { state, dispatch } = useApp();
  const { contract, finance, selectedBranch } = state;
  const [rep, setRep] = useState<DecisionReport | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!contract || !finance || !selectedBranch) { setLoading(false); return; }
    api.report(contract, finance, selectedBranch).then(setRep).catch(() => setRep(null)).finally(() => setLoading(false));
  }, [contract, finance, selectedBranch]);

  if (!contract || !finance || !selectedBranch) {
    return (
      <MobileShell>
        <div className="flex-1 flex flex-col items-center justify-center gap-3 px-6 text-center">
          <p className="text-sm text-muted-foreground">먼저 계약 입력과 갈래 선택이 필요해요.</p>
          <PrimaryBtn onClick={() => dispatch({ type: 'NAVIGATE', screen: 'SC-01' })}>처음으로</PrimaryBtn>
        </div>
      </MobileShell>
    );
  }

  const color = BRANCH_COLORS[selectedBranch];

  return (
    <MobileShell>
      <div className="flex items-center gap-2 px-5 py-3 border-b-2" style={{ borderColor: color }}>
        <BackBtn onClick={() => dispatch({ type: 'NAVIGATE', screen: 'SC-11' })} />
        <span className="font-bold" style={{ color }}>만기 결정 리포트</span>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
        {loading && <p className="text-sm text-muted-foreground text-center py-10">리포트를 만드는 중…</p>}

        {rep && (
          <>
            {/* ① 당신의 상황 */}
            <Section n="①" title="당신의 상황">
              <p className="text-sm font-semibold">{rep.persona.headline}</p>
              {(rep.clarify?.noteSignals?.length ?? 0) > 0 && (
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {rep.clarify!.noteSignals!.map((s, i) => (
                    <span key={i} className="text-[11px] px-2 py-0.5 bg-muted rounded-full text-muted-foreground">{s}</span>
                  ))}
                </div>
              )}
            </Section>

            {/* ② 세 갈래 채점 */}
            <Section n="②" title="세 갈래 채점">
              <div className="grid grid-cols-3 gap-2">
                {rep.comparison.branches.map(b => {
                  const on = b.branch === rep.selectedBranch;
                  return (
                    <div key={b.branch} className="rounded-xl p-2.5 text-center border-l-4"
                      style={{ borderColor: BRANCH_COLORS[b.branch], background: on ? COLORS.YELLOW_SURFACE : COLORS.CARD }}>
                      <p className="text-sm">{BRANCH_ICONS[b.branch]}</p>
                      <p className="text-[11px] font-medium" style={{ color: BRANCH_COLORS[b.branch] }}>{b.branch}</p>
                      <p className="text-sm font-bold mt-0.5">{man(b.monthlyBurden)}</p>
                    </div>
                  );
                })}
              </div>
              <p className="text-xs text-muted-foreground">선택: {BRANCH_ICONS[rep.selectedBranch]} {rep.selectedBranch}</p>
            </Section>

            {/* ③ 왜 이 동네 */}
            {rep.topRegion && (
              <Section n="③" title="왜 이 동네">
                <p className="text-sm font-semibold">{rep.topRegion.name} · 중위 {formatAmount(rep.topRegion.midPrice)}</p>
                {(rep.topRegion.scoreReasons ?? []).map((r, i) => (
                  <p key={i} className="text-xs text-muted-foreground">· {r}</p>
                ))}
                {rep.topRegion.jeonseRatio && (
                  <p className="text-xs" style={{ color: COLORS.SUB }}>
                    전세가율 {Math.round(rep.topRegion.jeonseRatio.ratio * 100)}% — {rep.topRegion.jeonseRatio.label}
                  </p>
                )}
              </Section>
            )}

            {/* ④ 그 동네의 하루 */}
            {rep.dayBrief && (
              <Section n="④" title="그 동네의 하루">
                <p className="text-sm leading-relaxed text-muted-foreground">{rep.dayBrief}</p>
              </Section>
            )}

            {/* ⑤ 지출로 본 실현 가능성 */}
            {rep.spend && (
              <Section n="⑤" title="지출로 본 실현 가능성">
                <div className="flex gap-2 text-center">
                  {[['월평균', rep.spend.monthlyTotal], ['고정', rep.spend.fixedMonthly], ['변동 여력', rep.spend.variableMonthly]].map(([l, v]) => (
                    <div key={l as string} className="flex-1 bg-muted rounded-xl py-2">
                      <p className="text-[11px] text-muted-foreground">{l}</p>
                      <p className="text-sm font-bold">{man(v as number)}</p>
                    </div>
                  ))}
                </div>
                <p className="text-sm mt-1" style={{ color: COLORS.TEXT }}>{rep.feasibility}</p>
                {(rep.spend.topCategories?.length ?? 0) > 0 && (
                  <p className="text-xs text-muted-foreground">
                    주요 지출: {rep.spend.topCategories.map(t => `${t.category} ${man(t.monthly)}`).join(' · ')}
                  </p>
                )}
                <p className="text-[11px] pt-1" style={{ color: COLORS.SUB }}>
                  ⚠️ 합성 시연 데이터 기준입니다. 실서비스에서는 마이데이터 동의 후 실제 내역으로 분석됩니다.
                </p>
              </Section>
            )}

            {/* ⑥ 다음 액션 */}
            <Section n="⑥" title="다음 액션">
              <p className="text-sm">갱신 통보 기한 <b>D-{rep.dday}</b> · 기한일 {rep.noticeDeadline}</p>
              <div className="flex gap-2 pt-1">
                <button onClick={() => dispatch({ type: 'NAVIGATE', screen: 'SC-10' })}
                  className="flex-1 py-2.5 rounded-xl text-sm font-semibold" style={{ background: COLORS.KB_YELLOW, color: COLORS.TEXT }}>
                  KB 상담 예약
                </button>
                <button onClick={() => dispatch({ type: 'NAVIGATE', screen: 'SC-11' })}
                  className="flex-1 py-2.5 rounded-xl text-sm font-semibold border" style={{ borderColor: COLORS.BORDER, color: COLORS.SUB }}>
                  저장·리마인더
                </button>
              </div>
            </Section>
          </>
        )}

        <Disclaimer />
      </div>
    </MobileShell>
  );
}
