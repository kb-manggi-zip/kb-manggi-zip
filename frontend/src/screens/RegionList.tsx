import React, { useEffect, useState, useMemo } from 'react';
import { useApp } from '../store';
import { COLORS, BRANCH_COLORS, BRANCH_ICONS } from '../theme';
import { MobileShell, JourneyHeader, BackBtn, Disclaimer, Accordion } from '../components/ui';
import AiBriefing from '../components/AiBriefing';
import { api, briefings, personaIdFor } from '../api/client';
import { formatAmount } from '../utils/format';
import { kbLandUrl } from '../utils/external';
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
    api.regions(selectedBranch, budget, state.contract?.housingType, state.contract?.preferredArea, state.finance?.household, applyNote ? note : '', personaIdFor(state.contract, state.finance), applyNote ? state.contract?.noteAdjust : undefined).then(setRegions);
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
  // 재택 등 통근 비중을 낮추기로 '확정'(noteAdjust)한 사용자면 통근을 '참고'로 격하(삭제 아님, G3)
  const deemphasizeCommute = applyNote && (state.contract?.noteAdjust?.commute ?? 1) < 0.95;

  // L3 미니 리포트 리드 신호 — 확정 신호만(실측>진술>세그먼트), 출처 규칙 유지. 보류 신호는 persona에 없음.
  const leadSignal = (() => {
    const sig = persona?.consumptionSignals ?? [];
    const pick = sig.find(s => s.source === '실측') ?? sig.find(s => s.source === '진술') ?? sig.find(s => s.source === '세그먼트');
    return pick?.label;
  })();

  // J4: 여러 후보가 공유하는 '구 기준' 동일 이유(구 폴백 유래)는 카드마다 반복하지 않고 상단 공통 안내로 접는다.
  const commonReasons = useMemo(() => {
    if (regions.length < 2) return [] as string[];
    const first = regions[0].scoreReasons ?? [];
    return first.filter(r => r.includes('구 기준') && regions.every(rg => (rg.scoreReasons ?? []).includes(r)));
  }, [regions]);
  // 모든 후보가 같은 구일 때만 '세 동네 모두 ○○구' 안내(구가 섞이면 접기 안 함)
  const guNames = Array.from(new Set(regions.map(r => (r.name || '').split(' ')[0]).filter(Boolean)));
  const commonGu = guNames.length === 1 ? guNames[0] : null;

  function selectRegion(r: Region) {
    dispatch({ type: 'SELECT_REGION', regionId: r.id, region: r });
    dispatch({ type: 'NAVIGATE', screen: 'SC-07' });
  }

  return (
    <MobileShell>
      <JourneyHeader step={4} dday={comparison?.dday} noticeDaysLeft={comparison?.noticeDaysLeft} />

      <div className="flex items-center gap-2 px-5 py-2 border-b-2" style={{ borderColor: color }}>
        <BackBtn onClick={() => dispatch({ type: 'NAVIGATE', screen: 'SC-03' })} />
        <span className="text-lg">{icon}</span>
        <span className="font-bold" style={{ color }}>
          {selectedBranch} · 예산 최대 {formatAmount(branch.depositOrPrice)}
        </span>
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
          {/* J4: 구 폴백으로 모든 후보가 동일한 값(통근·상권)은 카드 반복 대신 공통 안내 1줄로 접기 */}
          {commonReasons.length > 0 && (
            <div className="rounded-2xl border p-3 text-xs" style={{ borderColor: color + '44', background: color + '0A' }}>
              <p className="font-semibold mb-1" style={{ color }}>
                {commonGu ? `${regions.length}개 동네 모두 ${commonGu} — 아래는 구 기준 공통값이에요` : '아래는 구 기준 공통값이에요'}
              </p>
              {commonReasons.map((r, i) => (
                <p key={i} style={{ color: COLORS.SUB }}>· {r}</p>
              ))}
              <p className="mt-1 text-[11px]" style={{ color: COLORS.SUB }}>동 단위 데이터는 순차 수집 예정 · 아래 카드엔 동별로 다른 값만 표시해요</p>
            </div>
          )}
          {regions.map(r => (
            <RegionCard key={r.id} region={r} color={color} onSelect={() => selectRegion(r)}
              deemphasizeCommute={deemphasizeCommute} hiddenReasons={commonReasons} leadSignal={leadSignal} />
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
  const base = persona.baseWeights ?? {};
  const adjusted = weights.some(([k, v]) => Math.abs(v - (base[k] ?? v)) > 0.005);  // 자유입력이 가중치를 바꿨나
  const personal = (persona.consumptionSignals ?? []).filter(s => s.source !== '세그먼트');  // 실측·진술
  const segment = (persona.consumptionSignals ?? []).filter(s => s.source === '세그먼트');
  return (
    <div className="mx-5 mt-4 rounded-2xl border p-4 space-y-2" style={{ borderColor: color + '55', background: color + '0D' }}>
      <div className="flex items-center gap-2">
        <span className="text-base">🎯</span>
        <span className="font-bold text-sm" style={{ color }}>{persona.segment} 맞춤 추천</span>
      </div>
      {/* 개인 신호(실측·본인 진술)만 겉에 */}
      {personal.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {personal.map((s, i) => (
            <span key={i} title={s.reason} className="text-[11px] px-2 py-0.5 rounded-full"
              style={s.source === '실측' ? { background: color + '22', color, fontWeight: 600 } : { background: '#00000008', color: COLORS.SUB }}>
              {s.source === '실측' ? '실측 ' : ''}{s.label}
            </span>
          ))}
        </div>
      )}
      <p className="text-[11px] text-muted-foreground">{persona.budgetBand}</p>

      {/* 추천 기준 보기 — 세그먼트 가중치·근거는 접어둔다('당신은'이 아니라 '이 세그먼트는') */}
      <Accordion title="추천 기준 보기">
        <p className="text-[11px] pb-1">
          이 세그먼트는 동네를 볼 때 아래 순서로 봐요. 자유입력을 반영하면 여기 가중치가 함께 조정돼요.
          {adjusted && <span style={{ color }}> 회색 눈금 = 기본, 막대 = 반영 후.</span>}
        </p>
        <div className="space-y-1 py-1">
          {weights.map(([k, v]) => {
            const b = base[k] ?? v;
            const changed = Math.abs(v - b) > 0.005;
            return (
              <div key={k} className="flex items-center gap-2">
                <span className="text-xs w-14 shrink-0 text-muted-foreground">{AXIS_LABEL[k] ?? k}</span>
                <div className="relative flex-1 h-2 rounded-full overflow-hidden" style={{ background: '#0000000d' }}>
                  <div className="h-full rounded-full" style={{ width: `${Math.round(v * 100)}%`, background: color }} />
                  {/* 기본(before) 위치 눈금 — 반영으로 바뀐 축만 표시 */}
                  {adjusted && changed && (
                    <div className="absolute top-0 h-full" style={{ left: `${Math.round(b * 100)}%`, width: 2, background: COLORS.SUB, opacity: 0.55 }} />
                  )}
                </div>
                <span className="text-xs w-16 text-right tabular-nums text-muted-foreground">
                  {changed ? <span style={{ color }}>{Math.round(b * 100)}→{Math.round(v * 100)}%</span> : `${Math.round(v * 100)}%`}
                </span>
              </div>
            );
          })}
        </div>
        {/* 소비축 적합도 프레임 — '취향 추론'이 아니라 '자주 가는 곳이 가까운 동네'(G4) */}
        <p className="text-[11px] leading-snug pt-1" style={{ color: COLORS.SUB }}>
          · 생활·소비: 지출 내역은 자주 가는 곳의 기록이라, 그곳이 가까운 동네를 우선해요
        </p>
        <p className="text-[11px] leading-snug">근거: {persona.weightBasis}</p>
        {segment.length > 0 && (
          <p className="text-[11px] pt-1">이 세그먼트 소비 성향: {segment.map(s => s.label).join(' · ')}</p>
        )}
      </Accordion>
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

// 공용 접기 헬퍼(L2 월세 카드 패리티에서 재사용) — 구 폴백 동일 이유 + 단일 구명
export function foldedCommonReasons(regions: Region[]): string[] {
  if (regions.length < 2) return [];
  const first = regions[0].scoreReasons ?? [];
  return first.filter(r => r.includes('구 기준') && regions.every(rg => (rg.scoreReasons ?? []).includes(r)));
}
export function commonGuName(regions: Region[]): string | null {
  const gus = Array.from(new Set(regions.map(r => (r.name || '').split(' ')[0]).filter(Boolean)));
  return gus.length === 1 ? gus[0] : null;
}

export function RegionCard({ region, color, onSelect, deemphasizeCommute = false, hiddenReasons = [], subtitle, leadSignal }: { region: Region; color: string; onSelect: () => void; deemphasizeCommute?: boolean; hiddenReasons?: string[]; subtitle?: string; leadSignal?: string }) {
  // J4: 상단 공통 안내로 접힌 '구 기준' 이유는 카드에서 제외 → 동별로 다른 값만 남긴다
  const cardReasons = (region.scoreReasons ?? []).filter(r => !hiddenReasons.includes(r));
  // L3: 미니 리포트 요약 1줄 — {소비 신호} 당신에게 — {동네 차별 팩트}. 구 폴백 공통값은 차별 팩트 아님 → 제외.
  const summaryFacts = (() => {
    const distinct = cardReasons.filter(r => !r.includes('구 기준'));
    const bits: string[] = [];
    const dc = distinct.map(r => (r.match(/음식점·카페 \d+곳/) || [])[0]).find(Boolean);
    if (dc) bits.push(dc);
    if (region.surplus > 0) bits.push(`예산 여유 +${formatAmount(region.surplus)}`);
    if (bits.length === 0) bits.push(`중위 ${formatAmount(region.midPrice)}`, `실거래 ${region.tradeCount}건`);
    return bits.slice(0, 2).join(', ');
  })();
  // 통근이 접히지 않았을 때만(동별 실측) 칩 레벨에 표시 + 대표 직장 기준 각주
  const commuteFolded = hiddenReasons.some(r => r.includes('통근'));
  return (
    <div
      className="bg-card rounded-2xl border border-border p-4 transition-all"
      style={{ boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}
    >
    <button
      onClick={onSelect}
      className="w-full text-left space-y-3 active:scale-[0.98] transition-transform"
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="font-bold">{region.name}</p>
          <p className="text-sm text-muted-foreground">{subtitle ?? `중위가 ${formatAmount(region.midPrice)}`}</p>
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
      {/* 특징 한 줄 — 스코어 근거(통근) + region_facts(태그). 전부 실측/facts 값 */}
      {(() => {
        // 접힌(구 공통) 통근은 카드에서 빼고, 동별 통근만 칩으로. 대표 직장 기준은 '*' 각주로.
        let commute = commuteFolded ? undefined : cardReasons.map(r => (r.match(/통근 \d+분/) || [])[0]).find(Boolean);
        if (commute) commute = deemphasizeCommute ? `${commute} (참고)` : `${commute}*`;  // G3 참고 / J4 대표직장 각주
        const feature = [...region.tags, commute].filter(Boolean).slice(0, 3).join(' · ');
        return feature ? (
          <>
            <p className="text-xs" style={{ color: COLORS.SUB }}>{feature}</p>
            {commute && !deemphasizeCommute && (
              <p className="text-[10px]" style={{ color: COLORS.SUB }}>* 통근은 세그먼트 대표 직장 기준(문진에 직장 입력 없음)</p>
            )}
          </>
        ) : null;
      })()}
      <span className="text-xs text-muted-foreground">최근 실거래 {region.tradeCount}건</span>
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
      {/* L3 미니 리포트 요약 — 소비 신호 × 동네 차별 팩트(구 폴백 공통값 제외). 순수 템플릿(LLM 없음) */}
      <p className="text-xs font-medium pt-1" style={{ color }}>
        {leadSignal ? `${leadSignal} 당신에게 — ${summaryFacts}` : `이 동네 — ${summaryFacts}`}
      </p>
      {cardReasons.length > 0 && (
        <div className="text-xs space-y-0.5 pt-1" style={{ color: COLORS.SUB }}>
          <span className="font-semibold" style={{ color }}>왜 추천?</span>
          {cardReasons.map((r, i) => (
            <div key={i}>· {deemphasizeCommute && r.startsWith('통근') ? `${r} — 재택 반영, 참고용` : r}</div>
          ))}
        </div>
      )}
      <div className="flex items-center justify-between pt-1 border-t border-border">
        <p className="text-xs text-muted-foreground">하루 살아보기 →</p>
        <span className="text-xs font-semibold" style={{ color }}>이 동네 하루 보기 →</span>
      </div>
    </button>
      {/* 실매물 이어보기 — 발품을 대체하지 않고 좁혀서 잇는다(외부 링크, AI 큐레이션 아님) */}
      <a
        href={kbLandUrl(region.name)}
        target="_blank"
        rel="noopener noreferrer"
        onClick={e => e.stopPropagation()}
        className="mt-3 flex items-center justify-center gap-1 text-xs font-medium py-2 rounded-xl border"
        style={{ borderColor: color + '55', color }}
      >
        실매물은 KB부동산에서 이어보세요 →
      </a>
    </div>
  );
}
