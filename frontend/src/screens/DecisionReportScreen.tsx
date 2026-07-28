import React, { useEffect, useState } from 'react';
import { useApp } from '../store';
import { COLORS, BRANCH_COLORS, BRANCH_ICONS } from '../theme';
import { MobileShell, BackBtn, DdayBar } from '../components/ui';
import { formatAmount, ddayText } from '../utils/format';
import { kbLandUrl, officialProductUrl } from '../utils/external';
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

// Q1: 금융상품 한 행(태그·상품명·공식링크·설명). 상품명은 매칭되면 공식 페이지로 외부 링크(Q2).
function FinItem({ tag, name, url, sub, extra, icon, color }: {
  tag: string; name: string; url: string | null; sub?: string; extra?: string; icon?: string; color: string;
}) {
  return (
    <div className="rounded-xl p-3" style={{ background: COLORS.YELLOW_SURFACE }}>
      <div className="flex items-center gap-1.5 flex-wrap">
        <span className="text-[10px] font-bold px-1.5 py-0.5 rounded" style={{ background: color + '22', color }}>{tag}</span>
        {url ? (
          <a href={url} target="_blank" rel="noopener noreferrer" className="text-sm font-semibold underline underline-offset-2" style={{ color: COLORS.TEXT }}>
            {icon ? icon + ' ' : ''}{name} ↗
          </a>
        ) : (
          <span className="text-sm font-semibold" style={{ color: COLORS.TEXT }}>{icon ? icon + ' ' : ''}{name}</span>
        )}
      </div>
      {sub && <p className="text-xs mt-0.5 text-muted-foreground">{sub}</p>}
      {extra && <p className="text-sm font-bold mt-1" style={{ color }}>{extra}</p>}
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
  const selBranch = rep?.comparison.branches.find(b => b.branch === selectedBranch);
  const selBurden = selBranch?.monthlyBurden;
  // Q1: 갈래 → 필요 여신명(정보 병치)
  const loanName = selectedBranch === '매매' ? '주택담보대출' : selectedBranch === '이사' ? '신규 전세자금대출' : '증액분 전세자금대출';

  // P4: 이 사람 고유의 한 줄 결론 — 전부 '이미 계산된 값'만 결정론 조립(LLM 없음). 없는 요소는 생략.
  const oneLine = (() => {
    if (!rep) return '';
    const region1 = rep.topRegion?.name?.split(' ').pop();
    const withinBudget = /여력 안|안에 있어요/.test(rep.feasibility || '');
    const na = rep.nextAction;
    const bits = [
      `${selectedBranch}${region1 ? ` · ${region1}` : ''}`,
      selBurden != null ? `월 ${man(selBurden)}` : null,
      rep.spend ? (withinBudget ? '변동지출 여력 안' : '여력 초과 주의') : null,
      na?.eligible && na.annualSaving > 0 ? `${na.headline.split(' ')[0]} 자격 시 연 약 ${man(na.annualSaving)} 절감 가능` : null,
    ].filter(Boolean);
    return bits.join(' · ');
  })();

  return (
    <MobileShell>
      <DdayBar dday={rep?.dday} noticeDaysLeft={rep?.comparison.noticeDaysLeft} />
      <div className="flex items-center gap-2 px-5 py-2 border-b-2" style={{ borderColor: color }}>
        <BackBtn onClick={() => dispatch({ type: 'NAVIGATE', screen: 'SC-11' })} />
        <span className="font-bold" style={{ color }}>만기 결정 리포트</span>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
        {loading && <p className="text-sm text-muted-foreground text-center py-10">리포트를 만드는 중…</p>}

        {rep && (
          <>
            {/* 1층 — 상단 요약 카드(월부담) + P4 한 줄 결론 */}
            <div className="rounded-2xl p-4 text-center" style={{ background: color + '14', border: `1px solid ${color}44` }}>
              <p className="text-xs text-muted-foreground">{BRANCH_ICONS[selectedBranch]} {selectedBranch} · 월 부담</p>
              <p className="text-3xl font-bold my-1" style={{ color: COLORS.TEXT }}>{selBurden != null ? man(selBurden) : '—'}</p>
              <p className="text-xs" style={{ color: COLORS.SUB }}>{rep.feasibility}</p>
            </div>
            {/* P4: 이 사람 고유 한 줄 결론(결정론 조립) */}
            {oneLine && (
              <div className="rounded-2xl px-4 py-3" style={{ background: color + '0A', borderLeft: `3px solid ${color}` }}>
                <p className="text-sm font-semibold leading-snug" style={{ color: COLORS.TEXT }}>📌 {oneLine}</p>
                <p className="text-[11px] mt-0.5" style={{ color: COLORS.SUB }}>* 자격·금리는 정보 제공이며 실제 조건은 심사에 따라요(권유 아님).</p>
              </div>
            )}

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
                {/* P5: 발품 넘김 — 시세 기준임을 명시하고 실매물 확인은 KB부동산으로 잇는다(발품 대체 안 함) */}
                <p className="text-[11px] mt-1 pt-1 border-t border-border/50" style={{ color: COLORS.SUB }}>
                  여기 숫자는 이 동네 <b>실거래 시세 기준</b>이에요. 실제 매물·집주인 의사는 확인이 필요해요 — 아래 KB부동산에서 이어보세요.
                </p>
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

            <Section n="⑥" title="다음 액션 · KB 연결" open={!!open['⑥']} onToggle={() => toggle('⑥')}>
              {/* Q1: 금융상품은 여기 한 곳에서만, '자격 기준(동네 무관)'으로 3분류(필요 여신/자격 상품/보호 장치) */}
              <p className="text-[11px] mb-1.5" style={{ color: COLORS.SUB }}>
                아래는 <b>당신 자격 기준</b>이에요(동네와 무관). 정보 제공이며 권유가 아니에요.
              </p>

              {/* ① 필요 여신 — 갈래가 결정 */}
              <FinItem
                tag="필요 여신"
                color={color}
                name={loanName}
                url={officialProductUrl(loanName)}
                sub={`고르신 ${selectedBranch}에 필요한 대출`}
              />

              {/* ② 자격 상품 — 조건 충족 시 더 유리한 정책상품(버팀목·디딤돌 등) */}
              {rep.nextAction && (
                <FinItem
                  tag="자격 상품"
                  color={color}
                  name={rep.nextAction.headline}
                  url={officialProductUrl(rep.nextAction.headline)}
                  icon={rep.nextAction.eligible ? '💡' : '🔎'}
                  sub={rep.nextAction.detail}
                  extra={rep.nextAction.eligible && rep.nextAction.annualSaving > 0
                    ? `일반 기준 대비 연 약 ${man(rep.nextAction.annualSaving)} 절감(자격 충족 시)`
                    : undefined}
                />
              )}

              {/* ③ 보호 장치 — 전세(갱신·이사)에서 보증금 반환보증 */}
              {selectedBranch !== '매매' && selBranch?.guaranteeMonthly != null && selBranch.guaranteeMonthly > 0 && (
                <FinItem
                  tag="보호 장치"
                  color={color}
                  name="전세보증금 반환보증"
                  url={officialProductUrl('반환보증')}
                  sub={`보증료 월 약 ${man(selBranch.guaranteeMonthly)} — 보증금 미반환 위험 대비`}
                />
              )}

              {/* 지출 여력과 연결(⑤ 값 재사용) */}
              {rep.spend && selBurden != null && (
                <p className="text-[11px] mt-2" style={{ color: COLORS.SUB }}>
                  이 월 부담 {man(selBurden)}은 변동지출 여력 {man(rep.spend.variableMonthly)} {selBurden <= rep.spend.variableMonthly ? '안이에요' : '을 넘어요'}.
                </p>
              )}
              <p className="text-[11px] mt-0.5" style={{ color: COLORS.SUB }}>* 자격·한도·금리는 정보 제공이며 실제 조건은 KB 심사에 따라요(권유 아님).</p>

              <p className="text-sm mt-2">갱신 통보 기한 <b>{ddayText(rep.dday)}</b> · 기한일 {rep.noticeDeadline}</p>
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
