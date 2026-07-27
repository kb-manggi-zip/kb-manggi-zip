import React, { useEffect, useState } from 'react';
import { useApp } from '../store';
import { COLORS, BRANCH_COLORS, BRANCH_ICONS } from '../theme';
import { MobileShell, FlowProgress, BackBtn, Disclaimer, DdayBadge } from '../components/ui';
import AiBriefing from '../components/AiBriefing';
import { api, briefings } from '../api/client';
import { formatAmount } from '../utils/format';
import type { Region, PersonaProfile, ClarifyResult } from '../api/types';

export default function RegionList() {
  const { state, dispatch } = useApp();
  const { selectedBranch, comparison } = state;
  const [regions, setRegions] = useState<Region[]>([]);
  const [persona, setPersona] = useState<PersonaProfile | null>(null);
  const [clarify, setClarify] = useState<ClarifyResult | null>(null);
  // HITL — 자유입력 반영은 '제안'일 뿐, 사용자가 확정([반영할게요])해야 순위·가중치에 적용(E2E §2).
  const [applyNote, setApplyNote] = useState(false);
  const note = state.contract?.note ?? '';

  // 동네 순위 — 확정된 경우에만 note 보정을 반영(applyNote ? note : '').
  useEffect(() => {
    if (!selectedBranch || !comparison) return;
    const budget = comparison.branches.find(b => b.branch === selectedBranch)?.depositOrPrice || 0;
    api.regions(selectedBranch, budget, state.contract?.housingType, state.contract?.preferredArea, state.finance?.household, applyNote ? note : '').then(setRegions);
  }, [selectedBranch, comparison, state.contract?.housingType, state.contract?.preferredArea, state.finance?.household, note, applyNote]);

  // 개인화 프로필 카드 — 확정 여부에 따라 note를 넣거나 뺀 계약으로 조합(가중치가 확정에 반응).
  // budget = 고른 갈래 예산 → budgetBand가 실제로 표시됨.
  useEffect(() => {
    if (!state.contract || !state.finance || !selectedBranch || !comparison) return;
    const c = applyNote ? state.contract : { ...state.contract, note: '' };
    const budget = comparison.branches.find(b => b.branch === selectedBranch)?.depositOrPrice || 0;
    api.persona(c, state.finance, budget).then(setPersona).catch(() => setPersona(null));
  }, [state.contract, state.finance, applyNote, selectedBranch, comparison]);

  // 명확화 '제안'은 항상 실제 자유입력으로 계산(반영 여부와 무관하게 무엇을 제안할지 보여줌).
  useEffect(() => {
    if (!state.contract || !state.finance) return;
    api.clarify(state.contract, state.finance).then(setClarify).catch(() => setClarify(null));
  }, [state.contract, state.finance]);

  if (!selectedBranch || !comparison) return null;

  const branch = comparison.branches.find(b => b.branch === selectedBranch)!;
  const color = BRANCH_COLORS[selectedBranch];
  const icon = BRANCH_ICONS[selectedBranch];
  const briefText = regions.length > 0 ? briefings.regions(regions[0]) : null;

  function selectRegion(r: Region) {
    dispatch({ type: 'SELECT_REGION', regionId: r.id, region: r });
    dispatch({ type: 'NAVIGATE', screen: 'SC-07' });
  }

  return (
    <MobileShell>
      <FlowProgress current={3} />

      <div className="flex items-center gap-2 px-5 py-3 border-b-2" style={{ borderColor: color }}>
        <BackBtn onClick={() => dispatch({ type: 'NAVIGATE', screen: 'SC-03' })} />
        <span className="text-lg">{icon}</span>
        <span className="font-bold" style={{ color }}>
          {selectedBranch} · 예산 최대 {formatAmount(branch.depositOrPrice)}
        </span>
        {comparison && <span className="ml-auto"><DdayBadge dday={comparison.dday} /></span>}
      </div>

      <div className="flex-1 overflow-y-auto">
        {/* 미니 지도 스트립 */}
        <div
          className="mx-5 mt-4 rounded-2xl overflow-hidden relative"
          style={{ height: 130, background: '#E8EDF5' }}
        >
          <div className="absolute inset-0 flex items-center justify-center text-muted-foreground text-sm">
            📍 지도 미리보기
          </div>
          {regions.map((r, i) => (
            <div
              key={r.id}
              className="absolute text-xs font-bold"
              style={{ left: `${20 + i * 28}%`, top: `${30 + (i % 2) * 20}%`, color: COLORS.BLUE }}
            >
              📍{r.name.split(' ').pop()}
            </div>
          ))}
        </div>

        {/* 개인화 프로필 카드 — 완성 페르소나 → 조합된 리소스·근거 */}
        {persona && <PersonaCardView persona={persona} color={color} />}

        {/* 명확화 제안 + HITL 확정 — LLM은 제안만, 반영은 사용자가 확정(E2E §2 "확정은 사람이") */}
        {clarify && ((clarify.noteSignals?.length ?? 0) > 0 || (clarify.conflicts?.length ?? 0) > 0 || (clarify.questions?.length ?? 0) > 0) && (
          <ClarifyBanner
            clarify={clarify}
            applied={applyNote}
            onApply={() => { setApplyNote(true); api.hitl('applied', clarify.noteSignals ?? [], note); }}
            onSkip={() => { setApplyNote(false); api.hitl('skipped', clarify.noteSignals ?? [], note); }}
          />
        )}

        {/* AI 브리핑 */}
        {briefText && (
          <div className="mt-4">
            <AiBriefing text={briefText} />
          </div>
        )}

        <div className="px-5 py-3 space-y-3">
          <h2 className="text-base font-bold text-foreground">동네 후보</h2>
          {regions.some(r => r.jeonseRatio) && (
            <p className="text-xs text-muted-foreground -mt-1">
              실거래 중위가 대비 참고 지표예요. 실제 보증 가입은 선순위 채권과 기관 산정 주택가격 기준(HUG 90%)으로 심사돼요.
            </p>
          )}
          {regions.map(r => (
            <RegionCard key={r.id} region={r} color={color} onSelect={() => selectRegion(r)} />
          ))}
        </div>

        <Disclaimer />
      </div>
    </MobileShell>
  );
}

// 전세가율 구간 색 (판정·안내형 — 공포 아님): safe=민트, caution=옐로, alert=레드
function bandStyle(band: string): React.CSSProperties {
  if (band === 'safe') return { background: COLORS.MINT + '22', color: COLORS.MINT };
  if (band === 'alert') return { background: '#D6454522', color: '#C33' };
  return { background: COLORS.KB_YELLOW + '33', color: '#9A7B00' }; // caution
}

// 개인화 조합 산출물 — 세그먼트·우선순위 가중치·조합 리소스를 근거와 함께 노출(블랙박스 아님).
const AXIS_LABEL: Record<string, string> = { commute: '통근', consumption: '생활·소비', budget: '예산', preference: '선호지역' };
function PersonaCardView({ persona, color }: { persona: PersonaProfile; color: string }) {
  const weights = Object.entries(persona.weights).sort((a, b) => b[1] - a[1]);
  return (
    <div className="mx-5 mt-4 rounded-2xl border p-4 space-y-3" style={{ borderColor: color + '55', background: color + '0D' }}>
      <div className="flex items-center gap-2">
        <span className="text-base">🎯</span>
        <span className="font-bold text-sm" style={{ color }}>{persona.headline}</span>
      </div>
      {/* 우선순위 가중치 막대 — "감이 아니라 통계 근거" */}
      <div className="space-y-1">
        {weights.map(([k, v]) => (
          <div key={k} className="flex items-center gap-2">
            <span className="text-xs w-14 shrink-0 text-muted-foreground">{AXIS_LABEL[k] ?? k}</span>
            <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: '#0000000d' }}>
              <div className="h-full rounded-full" style={{ width: `${Math.round(v * 100)}%`, background: color }} />
            </div>
            <span className="text-xs w-9 text-right tabular-nums text-muted-foreground">{Math.round(v * 100)}%</span>
          </div>
        ))}
      </div>
      <p className="text-[11px] text-muted-foreground leading-snug">근거: {persona.weightBasis}</p>
      {/* 조합된 리소스 — 이 하루에 실제 등장할 것만('빼기의 개인화') */}
      <div className="flex flex-wrap gap-1.5 pt-1 border-t border-border/60">
        {persona.resources.map(r => (
          <span key={r} className="text-[11px] px-2 py-0.5 bg-muted rounded-full text-muted-foreground">{r}</span>
        ))}
      </div>
      <p className="text-[11px] text-muted-foreground">{persona.budgetBand}</p>
    </div>
  );
}

// 명확화 제안 + HITL 확정 — LLM(또는 규칙)이 '제안'하고, 반영은 사용자가 버튼으로 확정한다.
// 닫힌 루프: 제안 → [반영할게요/그대로 볼게요] → 확정된 것만 순위·가중치에 적용.
function ClarifyBanner({
  clarify, applied, onApply, onSkip,
}: { clarify: ClarifyResult; applied: boolean; onApply: () => void; onSkip: () => void }) {
  const signals = clarify.noteSignals ?? [];
  const conflicts = clarify.conflicts ?? [];
  const questions = (clarify.questions ?? []).filter(q => !conflicts.includes(q));
  return (
    <div className="mx-5 mt-3 rounded-2xl border p-3.5 space-y-2" style={{ borderColor: COLORS.KB_YELLOW, background: COLORS.YELLOW_SURFACE }}>
      <div className="flex items-center gap-1.5">
        <span className="text-sm">💬</span>
        <span className="text-xs font-bold" style={{ color: COLORS.TEXT }}>말씀하신 내용, 이렇게 반영할까요?</span>
      </div>

      {/* 확정 필요한 제안(자유입력 → 조정) */}
      {signals.length > 0 && (
        <>
          <div className="space-y-1">
            {signals.map((s, i) => (
              <p key={i} className="text-xs leading-snug" style={{ color: COLORS.SUB }}>· {s}</p>
            ))}
          </div>
          <div className="flex gap-2 pt-0.5">
            <button
              onClick={onApply}
              className="flex-1 text-xs font-semibold py-2 rounded-xl border transition-all"
              style={applied
                ? { background: COLORS.KB_YELLOW, borderColor: COLORS.KB_YELLOW, color: COLORS.TEXT }
                : { background: COLORS.CARD, borderColor: COLORS.BORDER, color: COLORS.SUB }}
            >
              {applied ? '✓ 반영했어요' : '반영할게요'}
            </button>
            <button
              onClick={onSkip}
              className="flex-1 text-xs font-semibold py-2 rounded-xl border transition-all"
              style={!applied
                ? { background: COLORS.CARD, borderColor: COLORS.TEXT, color: COLORS.TEXT }
                : { background: COLORS.CARD, borderColor: COLORS.BORDER, color: COLORS.SUB }}
            >
              그대로 볼게요
            </button>
          </div>
          <p className="text-[11px]" style={{ color: COLORS.SUB }}>
            {applied ? '동네 순위와 가중치에 반영됐어요.' : '반영 전에는 기본(가구 통계) 기준으로 보여드려요.'}
          </p>
        </>
      )}

      {/* 확인만 필요한 항목(모순·추가질문) — 반영 대상 아님 */}
      {(conflicts.length > 0 || questions.length > 0) && (
        <div className="space-y-1 pt-1 border-t border-border/60">
          {[...conflicts, ...questions].map((q, i) => (
            <p key={i} className="text-xs leading-snug" style={{ color: COLORS.SUB }}>· {q}</p>
          ))}
        </div>
      )}
    </div>
  );
}

function RegionCard({ region, color, onSelect }: { region: Region; color: string; onSelect: () => void }) {
  return (
    <button
      onClick={onSelect}
      className="w-full text-left bg-card rounded-2xl border border-border p-4 space-y-3 transition-all active:scale-[0.98]"
      style={{ boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="font-bold">{region.name}</p>
          <p className="text-sm text-muted-foreground">중위가 {formatAmount(region.midPrice)}</p>
        </div>
        {region.surplus > 0 && (
          <span
            className="text-xs font-semibold px-2.5 py-1 rounded-full"
            style={{ background: COLORS.MINT + '33', color: COLORS.MINT }}
          >
            +{formatAmount(region.surplus)} 여유
          </span>
        )}
      </div>
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs text-muted-foreground">최근 실거래 {region.tradeCount}건</span>
        {region.tags.map(t => (
          <span key={t} className="text-xs px-2 py-0.5 bg-muted rounded-full text-muted-foreground">{t}</span>
        ))}
      </div>
      {region.jeonseRatio && (
        <div className="flex items-center gap-1.5 flex-wrap" title={region.jeonseRatio.basis}>
          <span
            className="text-xs font-semibold px-2 py-0.5 rounded-full"
            style={bandStyle(region.jeonseRatio.band)}
          >
            전세가율 {Math.round(region.jeonseRatio.ratio * 100)}%
          </span>
          <span className="text-xs text-muted-foreground">{region.jeonseRatio.label}</span>
        </div>
      )}
      {region.scoreReasons && region.scoreReasons.length > 0 && (
        <div className="text-xs space-y-0.5 pt-1" style={{ color: COLORS.SUB }}>
          <span className="font-semibold" style={{ color }}>왜 추천?</span>
          {region.scoreReasons.map((r, i) => (
            <div key={i}>· {r}</div>
          ))}
        </div>
      )}
      <div className="flex items-center justify-between pt-1 border-t border-border">
        <p className="text-xs text-muted-foreground">하루 살아보기 →</p>
        <span className="text-xs font-semibold" style={{ color }}>이 동네 하루 보기 →</span>
      </div>
    </button>
  );
}
