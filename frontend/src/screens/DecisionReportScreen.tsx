import React, { useEffect, useState } from 'react';
import { useApp } from '../store';
import { COLORS, BRANCH_COLORS, BRANCH_ICONS } from '../theme';
import { MobileShell, BackBtn, JourneyHeader } from '../components/ui';
import { formatAmount, ddayText } from '../utils/format';
import { kbLandUrl } from '../utils/external';
import { api } from '../api/client';
import type { DecisionReport } from '../api/types';

const man = (won: number) => `${Math.round(won / 10_000).toLocaleString()}만원`;

// 접히는 리포트 섹션 — 헤더 탭으로 펼침(스크롤 지옥 방지). 1층은 상단 요약 카드가 담당.
function Section({ n, title, open, onToggle, children }: {
  n: string; title: string; open: boolean; onToggle: () => void; children: React.ReactNode;
}) {
  return (
    <div className="bg-card rounded-2xl border border-border overflow-hidden">
      <button onClick={onToggle} className="w-full flex items-center gap-2 px-4 py-3">
        <span className="text-xs font-bold w-5 h-5 rounded-full flex items-center justify-center shrink-0"
          style={{ background: COLORS.KB_YELLOW, color: COLORS.TEXT }}>{n}</span>
        <h2 className="text-sm font-bold flex-1 text-left" style={{ color: COLORS.TEXT }}>{title}</h2>
        <span className="text-xs text-muted-foreground">{open ? '접기' : '자세히'}</span>
      </button>
      {open && <div className="px-4 pb-4 space-y-2">{children}</div>}
    </div>
  );
}

export default function DecisionReportScreen() {
  const { state, dispatch } = useApp();
  const { contract, finance, selectedBranch, selectedRegionId } = state;
  const [rep, setRep] = useState<DecisionReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState<Record<string, boolean>>({ '⑤': true }); // ⑤ 지출만 기본 펼침(핵심 신규)
  const toggle = (k: string) => setOpen(o => ({ ...o, [k]: !o[k] }));

  useEffect(() => {
    if (!contract || !finance || !selectedBranch) { setLoading(false); return; }
    api.report(contract, finance, selectedBranch, undefined, selectedRegionId ?? undefined)
      .then(setRep).catch(() => setRep(null)).finally(() => setLoading(false));
  }, [contract, finance, selectedBranch, selectedRegionId]);

  if (!contract || !finance || !selectedBranch) {
    return (
      <MobileShell>
        <div className="flex-1 flex flex-col items-center justify-center gap-3 px-6 text-center">
          <p className="text-sm text-muted-foreground">먼저 계약 입력과 갈래 선택이 필요해요.</p>
          <button onClick={() => dispatch({ type: 'NAVIGATE', screen: 'SC-01' })}
            className="px-4 py-2 rounded-xl font-semibold text-sm" style={{ background: COLORS.KB_YELLOW }}>처음으로</button>
        </div>
      </MobileShell>
    );
  }

  const color = BRANCH_COLORS[selectedBranch];
  const selBurden = rep?.comparison.branches.find(b => b.branch === selectedBranch)?.monthlyBurden;

  return (
    <MobileShell>
      <JourneyHeader step={7} dday={rep?.dday} noticeDaysLeft={rep?.comparison.noticeDaysLeft} />
      <div className="flex items-center gap-2 px-5 py-2 border-b-2" style={{ borderColor: color }}>
        <BackBtn onClick={() => dispatch({ type: 'NAVIGATE', screen: 'SC-11' })} />
        <span className="font-bold" style={{ color }}>만기 결정 리포트</span>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
        {loading && <p className="text-sm text-muted-foreground text-center py-10">리포트를 만드는 중…</p>}

        {rep && (
          <>
            {/* 1층 — 상단 요약 카드(헤드라인 하나) */}
            <div className="rounded-2xl p-4 text-center" style={{ background: color + '14', border: `1px solid ${color}44` }}>
              <p className="text-xs text-muted-foreground">{BRANCH_ICONS[selectedBranch]} {selectedBranch} · 월 부담</p>
              <p className="text-3xl font-bold my-1" style={{ color: COLORS.TEXT }}>{selBurden != null ? man(selBurden) : '—'}</p>
              <p className="text-xs" style={{ color: COLORS.SUB }}>{rep.feasibility}</p>
            </div>

            {/* ①~⑥ 접힘 카드 */}
            <Section n="①" title="당신의 상황" open={!!open['①']} onToggle={() => toggle('①')}>
              <p className="text-sm font-semibold">{rep.persona.headline}</p>
              <div className="flex flex-wrap gap-1.5">
                {(rep.persona.consumptionSignals ?? []).map((s, i) => (
                  <span key={i} title={s.reason} className="text-[11px] px-2 py-0.5 rounded-full"
                    style={s.source === '실측' ? { background: color + '22', color, fontWeight: 600 } : { background: '#00000008', color: COLORS.SUB }}>
                    {s.source === '실측' ? '실측 ' : ''}{s.label}
                  </span>
                ))}
              </div>
            </Section>

            <Section n="②" title="세 갈래 채점" open={!!open['②']} onToggle={() => toggle('②')}>
              <div className="grid grid-cols-3 gap-2">
                {rep.comparison.branches.map(b => (
                  <div key={b.branch} className="rounded-xl p-2.5 text-center border-l-4"
                    style={{ borderColor: BRANCH_COLORS[b.branch], background: b.branch === selectedBranch ? COLORS.YELLOW_SURFACE : COLORS.CARD }}>
                    <p className="text-sm">{BRANCH_ICONS[b.branch]}</p>
                    <p className="text-[11px] font-medium" style={{ color: BRANCH_COLORS[b.branch] }}>{b.branch}</p>
                    <p className="text-sm font-bold mt-0.5">{man(b.monthlyBurden)}</p>
                  </div>
                ))}
              </div>
            </Section>

            {rep.topRegion ? (
              <Section n="③" title={`왜 이 동네${rep.topRegion ? ` (${rep.topRegion.name.split(' ').pop()} 기준)` : ''}`} open={!!open['③']} onToggle={() => toggle('③')}>
                <p className="text-sm font-semibold">{rep.topRegion.name} · 중위 {formatAmount(rep.topRegion.midPrice)}</p>
                {(rep.topRegion.scoreReasons ?? []).map((r, i) => <p key={i} className="text-xs text-muted-foreground">· {r}</p>)}
                {rep.topRegion.jeonseRatio && (
                  <p className="text-xs" style={{ color: COLORS.SUB }}>전세가율 {Math.round(rep.topRegion.jeonseRatio.ratio * 100)}% — {rep.topRegion.jeonseRatio.label}</p>
                )}
              </Section>
            ) : selectedBranch === '갱신' && (
              // 갱신은 새 동네 추천이 없음 → 현재 동네 유지를 명시(빈 구간 방지, B7)
              <Section n="③" title="현재 동네 유지" open={!!open['③']} onToggle={() => toggle('③')}>
                <p className="text-sm leading-relaxed text-muted-foreground">
                  갱신은 지금 동네를 그대로 이어가는 선택이에요. 새로 추천할 동네도, 발품도 없어요.
                </p>
              </Section>
            )}

            {rep.dayBrief && (
              <Section n="④" title={selectedBranch === '갱신' ? '유지하는 하루' : `그 동네의 하루${rep.topRegion ? ` (${rep.topRegion.name.split(' ').pop()} 기준)` : ''}`} open={!!open['④']} onToggle={() => toggle('④')}>
                <p className="text-sm leading-relaxed text-muted-foreground">{rep.dayBrief}</p>
              </Section>
            )}

            {rep.spend && (
              <Section n="⑤" title="지출로 본 실현 가능성" open={!!open['⑤']} onToggle={() => toggle('⑤')}>
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
                  <p className="text-xs text-muted-foreground">주요 지출: {rep.spend.topCategories.map(t => `${t.category} ${man(t.monthly)}`).join(' · ')}</p>
                )}
                <p className="text-[11px] pt-1" style={{ color: COLORS.SUB }}>⚠️ 합성 시연 데이터 기준입니다. 실서비스에서는 마이데이터 동의 후 실제 내역으로 분석됩니다.</p>
              </Section>
            )}

            <Section n="⑥" title="다음 액션" open={!!open['⑥']} onToggle={() => toggle('⑥')}>
              {rep.nextAction && (
                <div className="mb-2 rounded-xl p-3" style={{ background: COLORS.YELLOW_SURFACE }}>
                  <p className="text-sm font-semibold" style={{ color: COLORS.TEXT }}>
                    {rep.nextAction.eligible ? '💡 ' : '🔎 '}{rep.nextAction.headline}
                  </p>
                  <p className="text-xs mt-0.5 text-muted-foreground">{rep.nextAction.detail}</p>
                  {rep.nextAction.eligible && rep.nextAction.annualSaving > 0 && (
                    <p className="text-sm font-bold mt-1" style={{ color: color }}>연 약 {man(rep.nextAction.annualSaving)} 절감</p>
                  )}
                </div>
              )}
              <p className="text-sm">갱신 통보 기한 <b>{ddayText(rep.dday)}</b> · 기한일 {rep.noticeDeadline}</p>
              {/* 이사·매매면 그 동네 실매물을 KB부동산에서 이어보기(외부 링크·AI 큐레이션 아님) */}
              {rep.topRegion && (
                <a
                  href={kbLandUrl(rep.topRegion.name)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-2 flex items-center justify-center gap-1 text-xs font-medium py-2 rounded-xl border"
                  style={{ borderColor: color + '55', color }}
                >
                  {rep.topRegion.name} 실매물은 KB부동산에서 이어보세요 →
                </a>
              )}
            </Section>
          </>
        )}
      </div>

      {/* 하단 고정 — 다음 액션이 항상 보이게 */}
      {rep && (
        <div className="px-5 py-3 border-t border-border flex items-center gap-3" style={{ background: COLORS.CARD }}>
          <div className="flex-1">
            <p className="text-[11px] text-muted-foreground">갱신 통보 기한</p>
            <p className="text-sm font-bold" style={{ color: COLORS.CORAL }}>{ddayText(rep.dday)}</p>
          </div>
          <button onClick={() => dispatch({ type: 'NAVIGATE', screen: 'SC-10' })}
            className="px-5 py-2.5 rounded-xl text-sm font-bold" style={{ background: COLORS.KB_YELLOW, color: COLORS.TEXT }}>
            KB 상담 예약
          </button>
        </div>
      )}
    </MobileShell>
  );
}
