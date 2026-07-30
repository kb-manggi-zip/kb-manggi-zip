import React, { useEffect, useState, useRef } from 'react';
import { useApp } from '../store';
import { COLORS, BRANCH_COLORS, BRANCH_ICONS } from '../theme';
import { MobileShell, BackBtn, DdayBar } from '../components/ui';
import { formatAmount, ddayText } from '../utils/format';
import { kbLandUrl, officialProductUrl } from '../utils/external';
import { api, briefings } from '../api/client';
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
  const [loading, setLoading] = useState(true);   // 최초 로드(리포트 없음)
  const [switching, setSwitching] = useState(false); // 갈래 전환 재조회 중(이전 리포트 유지)
  const [switchError, setSwitchError] = useState<string | null>(null);
  const [open, setOpen] = useState<Record<string, boolean>>({ '②': true, '⑤': true }); // ② 전환 컨트롤 + ⑤ 지출 기본 펼침
  const toggle = (k: string) => setOpen(o => ({ ...o, [k]: !o[k] }));
  const repRef = useRef<DecisionReport | null>(null);
  useEffect(() => { repRef.current = rep; }, [rep]);

  useEffect(() => {
    if (!contract || !finance || !selectedBranch) { setLoading(false); return; }
    let cancelled = false;
    const hadRep = repRef.current != null;
    // 전환 재조회는 이전 리포트를 지우지 않고 로딩만 표시(R5 조건②: 깨짐/이전값 노출 방지)
    if (hadRep) setSwitching(true); else setLoading(true);
    setSwitchError(null);
    api.report(contract, finance, selectedBranch, undefined, selectedRegionId ?? undefined)
      .then(r => { if (!cancelled) setRep(r); })
      .catch(() => {
        if (cancelled) return;
        // 실패 시: 이전 리포트가 있으면 그대로 유지(화면은 rep.selectedBranch 기준이라 정합 유지), 안내만.
        if (repRef.current) setSwitchError(`‘${selectedBranch}’ 기준 재계산에 실패했어요 — 이전 리포트를 유지했어요.`);
        else setRep(null);
      })
      .finally(() => { if (!cancelled) { setLoading(false); setSwitching(false); } });
    return () => { cancelled = true; };
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

  // 화면은 항상 '지금 렌더된 리포트의 갈래(rep.selectedBranch)' 기준 — 전환/실패 중에도 리포트 내부 정합 보장.
  // store의 selectedBranch는 '요청한 갈래'(fetch 트리거)일 뿐, 표시는 shown으로 통일.
  const shown = rep?.selectedBranch ?? selectedBranch;
  const color = BRANCH_COLORS[shown];
  const selBranch = rep?.comparison.branches.find(b => b.branch === shown);
  const selBurden = selBranch?.monthlyBurden;
  // Q1: 갈래 → 필요 여신명(정보 병치)
  const loanName = shown === '매매' ? '주택담보대출' : shown === '이사' ? '신규 전세자금대출' : '증액분 전세자금대출';
  // R5: 관점 선언 + 비교 잔상(결정론·compare 값 재사용)
  const perspective = rep ? briefings.reportPerspective(rep.comparison, shown, man) : null;

  // P4: 이 사람 고유의 한 줄 결론 — 전부 '이미 계산된 값'만 결정론 조립(LLM 없음). 없는 요소는 생략.
  const oneLine = (() => {
    if (!rep) return '';
    const region1 = rep.topRegion?.name?.split(' ').pop();
    const withinBudget = /여력 안|안에 있어요/.test(rep.feasibility || '');
    const na = rep.nextAction;
    const bits = [
      `${shown}${region1 ? ` · ${region1}` : ''}`,
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

        {/* R5 조건②: 전환 실패 시 이전 리포트 유지 + 안내 */}
        {switchError && (
          <div className="rounded-xl px-3 py-2 text-xs" style={{ background: '#FDECEC', color: '#B42318' }}>
            {switchError}
          </div>
        )}
        {/* R5 조건②: 전환 재조회 중 로딩 표시(이전 리포트는 dim 처리, 값 오인 방지) */}
        {switching && (
          <div className="flex items-center justify-center gap-2 rounded-xl px-3 py-2 text-xs" style={{ background: color + '14', color }}>
            <span className="inline-block w-3 h-3 rounded-full border-2 border-current border-t-transparent animate-spin" />
            ‘{selectedBranch}’ 기준으로 다시 계산 중…
          </div>
        )}

        {rep && (
          <div className={`space-y-3 ${switching ? 'opacity-40 pointer-events-none' : ''}`}>
            {/* 1층 — 상단 요약 카드(월부담) + P4 한 줄 결론 */}
            <div className="rounded-2xl p-4 text-center" style={{ background: color + '14', border: `1px solid ${color}44` }}>
              <p className="text-xs text-muted-foreground">{BRANCH_ICONS[shown]} {shown} · 월 부담</p>
              <p className="text-3xl font-bold my-1" style={{ color: COLORS.TEXT }}>{selBurden != null ? man(selBurden) : '—'}</p>
              <p className="text-xs" style={{ color: COLORS.SUB }}>{rep.feasibility}</p>
            </div>
            {/* R5: 관점 선언 + 비교 잔상 — 고른 길이 중심이되 비교 맥락을 리포트 안에 유지(결정론) */}
            {perspective && (
              <div className="rounded-2xl px-4 py-3 space-y-0.5" style={{ background: color + '0A', border: `1px solid ${color}22` }}>
                <p className="text-sm font-semibold" style={{ color: COLORS.TEXT }}>🧭 {perspective.declare}</p>
                {perspective.contrast && <p className="text-xs leading-relaxed" style={{ color: COLORS.SUB }}>{perspective.contrast}</p>}
                <p className="text-[11px] pt-0.5" style={{ color: COLORS.SUB }}>아래 <b>‘세 갈래 채점’</b>에서 갈래를 눌러 다른 기준으로 바꿔볼 수 있어요.</p>
              </div>
            )}
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
                {rep.comparison.branches.map(b => {
                  const active = b.branch === shown;
                  return (
                    // R5: 칩을 눌러 그 갈래 기준으로 리포트 전체를 다시 봄(SELECT_BRANCH → 재조회)
                    <button
                      key={b.branch}
                      onClick={() => { if (!active) dispatch({ type: 'SELECT_BRANCH', branch: b.branch }); }}
                      aria-pressed={active}
                      className="rounded-xl p-2.5 text-center border-l-4 transition-transform active:scale-[0.97]"
                      style={{
                        borderColor: BRANCH_COLORS[b.branch],
                        background: active ? COLORS.YELLOW_SURFACE : COLORS.CARD,
                        boxShadow: active ? `0 0 0 2px ${BRANCH_COLORS[b.branch]}55` : 'none',
                      }}
                    >
                      <p className="text-sm">{BRANCH_ICONS[b.branch]}</p>
                      <p className="text-[11px] font-medium" style={{ color: BRANCH_COLORS[b.branch] }}>{b.branch}</p>
                      <p className="text-sm font-bold mt-0.5">{man(b.monthlyBurden)}</p>
                    </button>
                  );
                })}
              </div>
              <p className="text-[11px] mt-2 text-center" style={{ color: COLORS.SUB }}>👆 갈래를 눌러 다른 기준으로 리포트를 다시 볼 수 있어요</p>
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
            ) : shown === '갱신' && (
              // 갱신은 새 동네 추천이 없음 → 현재 동네 유지를 명시(빈 구간 방지, B7)
              <Section n="③" title="현재 동네 유지" open={!!open['③']} onToggle={() => toggle('③')}>
                <p className="text-sm leading-relaxed text-muted-foreground">
                  갱신은 지금 동네를 그대로 이어가는 선택이에요. 새로 추천할 동네도, 발품도 없어요.
                </p>
              </Section>
            )}

            {rep.dayBrief && (
              <Section n="④" title={shown === '갱신' ? '유지하는 하루' : `그 동네의 하루${rep.topRegion ? ` (${rep.topRegion.name.split(' ').pop()} 기준)` : ''}`} open={!!open['④']} onToggle={() => toggle('④')}>
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
                sub={`고르신 ${shown}에 필요한 대출`}
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
              {shown !== '매매' && selBranch?.guaranteeMonthly != null && selBranch.guaranteeMonthly > 0 && (
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

              {/* 이사·매매면 그 동네 실매물을 KB부동산에서 이어보기(외부 링크·AI 큐레이션 아님) */}
              {rep.topRegion && (
                <a
                  href={kbLandUrl(rep.topRegion.lat, rep.topRegion.lng)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-2 flex items-center justify-center gap-1 text-xs font-medium py-2 rounded-xl border"
                  style={{ borderColor: color + '55', color }}
                >
                  {rep.topRegion.name} 실매물은 KB부동산에서 이어보세요 →
                </a>
              )}
            </Section>
          </div>
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
