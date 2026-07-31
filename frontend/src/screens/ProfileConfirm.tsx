import React, { useEffect, useState } from 'react';
import { useApp } from '../store';
import { COLORS } from '../theme';
import { MobileShell, PrimaryBtn, DdayBar } from '../components/ui';
import { formatAmount } from '../utils/format';
import { eunNeun, eulReul } from '../utils/josa';
import { api, RENEWAL_SITUATION_INFO, dirSign } from '../api/client';
import type { PersonaProfile, ClarifyResult, AxisDirection } from '../api/types';

function householdLabel(h: string) {
  return h === '1인' ? '1인 가구' : h === '신혼' ? '신혼 가구' : '자녀 가구';
}

// 축 → 사용자 언어(화면엔 '축/배수/가중치' 안 씀)
const AXIS_UI: Record<string, { label: string; icon: string }> = {
  commute: { label: '통근', icon: '🚇' },
  consumption: { label: '동네 생활·편의', icon: '🏘' },
  budget: { label: '예산 여유', icon: '💵' },
  preference: { label: '원하는 지역', icon: '📍' },
};
const RETAK_RE = /재택|집에서|집 주변|동네에서|근처에서/;
// 확장 추론: 재택류 입력이 동네환경(consumption)을 올릴 때 = 한 단계 건너뛴 추론 → 그 단계를 드러냄
function isExtended(note: string, axis: string): boolean {
  return axis === 'consumption' && RETAK_RE.test(note);
}
// 카드 문구 = 축 + 방향만(원문 인용은 그룹 헤더에 1회만, 카드 반복 인용 금지).
//   더/덜은 방향 부호에서 파생(up류='더', down류='덜'). strong 여부는 화면에 안 드러냄(기존 원칙).
function cardRationale(note: string, axis: string, direction: string): string {
  if (isExtended(note, axis)) return '재택이면 동네에서 보내는 시간이 길어서, 동네 생활·편의를 더 볼까요?';
  const dir = dirSign(direction) > 0 ? '더' : '덜';
  const label = AXIS_UI[axis]?.label ?? axis;
  return `${label}${eunNeun(label)} ${dir} 중요하게 볼게요.`;
}

// 문진 완료 직후 1회 — '당신의 프로필'. 확실한 것만: 사실 + 칩(사실 파생·본인 진술·실측). 가중치 바·세그먼트 통계 칩 없음.
export default function ProfileConfirm() {
  const { state, dispatch } = useApp();
  const { contract, finance, comparison } = state;
  const [persona, setPersona] = useState<PersonaProfile | null>(null);
  const [validation, setValidation] = useState<ClarifyResult | null>(null);
  const [acceptedPairs, setAcceptedPairs] = useState<string[][]>([]);  // '둘 다 맞아요'로 확인한 쌍(K1)
  const [applied, setApplied] = useState(false);
  const [tooltip, setTooltip] = useState<string | null>(null);
  // C: 제안 카드 개별 승인/거절 상태(축 key 또는 'renewal'). 확정 전엔 '확인 대기'.
  const [approved, setApproved] = useState<Set<string>>(new Set());
  const [rejected, setRejected] = useState<Set<string>>(new Set());
  const [showExt, setShowExt] = useState(false); // 확장 추론 카드 펼침
  const [convAmount, setConvAmount] = useState(''); // 전환 감액분 입력(만원). 프리필=clarify 추출

  // 예산(참고) — 예산↔선호 상충 판단 맥락. 갈래 미선택이라 대표로 전세(이사) 예산 사용.
  const refBudget = comparison?.branches.find(b => b.branch === '이사')?.depositOrPrice
    ?? comparison?.branches?.[0]?.depositOrPrice ?? 0;

  useEffect(() => {
    if (!contract || !finance) { dispatch({ type: 'NAVIGATE', screen: 'SC-03' }); return; }
    api.persona(contract, finance).then(setPersona).catch(() => setPersona(null));
    // 최종 프로필 종합검증(SC-14 1회): 누적 자유입력 전체 + 가구 + 예산을 한 번에 검증(원격 AI / 로컬 간이).
    // acceptedPairs 변하면 재검증(둘 다 맞아요로 확인한 쌍 제외).
    api.validateProfile(contract, finance, refBudget, true, acceptedPairs).then(setValidation).catch(() => setValidation(null));
    setApplied(false);
    setApproved(new Set()); setRejected(new Set()); setShowExt(false); setConvAmount(''); // 재검증 시 카드 상태 초기화
  }, [contract, finance, acceptedPairs]); // eslint-disable-line react-hooks/exhaustive-deps

  // 전환 감액분 프리필 — clarify가 자유입력에서 뽑았으면 사람이 확정하도록 채워둠(원→만원)
  useEffect(() => {
    if (validation?.conversionAmount != null) setConvAmount(String(Math.round(validation.conversionAmount / 10000)));
  }, [validation]);

  if (!contract || !finance) return null;

  const items = validation?.conflictItems ?? [];
  const noteSignals = validation?.noteSignals ?? [];
  const hasNote = !!contract.note?.trim();
  const isRuleMode = validation?.mode === 'rule';
  const held = !!validation?.held;
  const hasAdjust = !held && !!validation?.weightAdjust && Object.keys(validation.weightAdjust).length > 0;

  // ── C: 축별 제안 카드 파생(1카드=1축). 직접 추론 먼저, 확장 추론(재택→동네환경)은 접어서 뒤로 ──
  const note = contract.note ?? '';
  const adjust: Record<string, string> = (!held && validation?.weightAdjust) || {};
  const axisCards = Object.entries(adjust).map(([axis, direction]) => ({ axis, direction, ext: isExtended(note, axis) }));
  const directCards = axisCards.filter(c => !c.ext);
  const extCards = axisCards.filter(c => c.ext);
  const renewalPct = validation?.renewalAskPct ?? null;
  // 갱신 상황 카드 — 닫힌 enum 분류(unknown은 카드 없이 consultNote로만). 4축과 무게가 달라 별도 표시.
  const situations = (validation?.renewalSituations ?? []).filter(s => s !== 'unknown');
  const sitEvidence = validation?.situationEvidence ?? {};
  const cardState = (key: string) => (approved.has(key) ? 'approved' : rejected.has(key) ? 'rejected' : 'pending');
  function approve(key: string) { setApproved(s => new Set(s).add(key)); setRejected(s => { const n = new Set(s); n.delete(key); return n; }); }
  function reject(key: string) { setRejected(s => new Set(s).add(key)); setApproved(s => { const n = new Set(s); n.delete(key); return n; }); }
  function undo(key: string) { setApproved(s => { const n = new Set(s); n.delete(key); return n; }); setRejected(s => { const n = new Set(s); n.delete(key); return n; }); }
  function approveAllDirect() { setApproved(s => { const n = new Set(s); directCards.forEach(c => n.add(c.axis)); if (renewalPct != null) n.add('renewal'); return n; }); }

  // ── 인라인 해소(K1): 되묻기의 목적은 재입력이 아니라 확인 ──
  const notesOf = () => (contract!.note ?? '').split(' · ').map(s => s.trim()).filter(Boolean);
  function removeNote(loser: string) {  // A/B 선택 → 안 고른 신호 제거
    const notes = notesOf().filter(n => n !== loser);
    dispatch({ type: 'SET_CONTRACT', contract: { ...contract!, note: notes.join(' · '), noteAdjust: {} } });
  }
  function acceptPair(pair: string[]) {  // '둘 다 맞아요' → 그 쌍은 상충으로 안 봄(사용자 확인한 상쇄)
    setAcceptedPairs(p => [...p, pair]);
  }
  function changeHousehold(seg: string) {  // 가구 유형 상충 → 문진 복귀 없이 갱신
    dispatch({ type: 'SET_FINANCE', finance: { ...finance!, household: seg as typeof finance.household } });
  }

  // HITL 확정: '승인한 축만' noteAdjust에 실린다(거절·확인대기는 미반영). 승인→noteAdjust→랭킹 흐름은 그대로.
  function applyAndCompare() {
    const noteAdjust: Record<string, AxisDirection> = {};
    axisCards.forEach(({ axis, direction }) => { if (approved.has(axis)) noteAdjust[axis] = direction as AxisDirection; });
    const patch: typeof contract = {
      ...contract!,
      noteAdjust,
      // ★ D-7: 승인이 0건이면 noteAdjust가 비어 '키워드 폴백'이 미승인 신호를 되살리므로 원문 note를 비운다.
      //   승인이 1건↑이면 noteAdjust(비어있지 않음)가 랭킹을 주도하므로 note는 유지(리포트에 진술 칩 표시).
      //   상담 사정은 승인과 무관하게 항상 consultNote로 보존.
      note: approved.size > 0 ? contract!.note : '',
      // 상담 사정 = 갱신 스텝 직접입력(contract.consultNote) + 자유입력에서 추출분(validation) 병합(원문·중복 제거)
      consultNote: Array.from(new Set(
        [(contract!.consultNote || '').trim(), (validation?.consultNote || '').trim()].filter(Boolean)
      )).join(' · '),
    };
    // 인상률 카드 승인 시에만 확정분으로 반영(미승인이면 null 유지 → 계산 불변)
    patch.renewalAskPct = (approved.has('renewal') && renewalPct != null) ? renewalPct : null;
    // 갱신 상황: 승인분만 확정 → compare resolver가 requires 재검증 후 반영. 미승인은 계산 미반영.
    patch.renewalSituations = situations.filter(s => approved.has('sit:' + s));
    // 전환 감액분: jeonse_to_monthly 승인 + 입력 있을 때만(만원→원). 미입력/미승인이면 null → 전환 미계산(안내만).
    patch.conversionAmount = (approved.has('sit:jeonse_to_monthly') && convAmount.trim() !== '')
      ? parseInt(convAmount, 10) * 10_000 : null;
    dispatch({ type: 'SET_CONTRACT', contract: patch });
    dispatch({ type: 'NAVIGATE', screen: 'SC-03' });
  }

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

        {/* 최종 프로필 종합검증 결과 — 자유입력이 있을 때만. 상충이면 정정 유도, 아니면 해석 확인 후 반영(HITL) */}
        {hasNote && validation && (
          <div className="rounded-2xl p-4 space-y-2"
            style={{ background: COLORS.YELLOW_SURFACE, border: `1px solid ${COLORS.KB_YELLOW}` }}>
            <div className="flex items-center gap-2">
              <p className="text-sm font-bold" style={{ color: COLORS.KB_GRAY }}>
                {items.length > 0 ? '몇 가지만 확인할게요' : '🤖 입력을 이렇게 이해했어요'}
              </p>
              <span className="text-[10px] px-1.5 py-0.5 rounded-full"
                style={{ background: isRuleMode ? '#00000010' : COLORS.KB_YELLOW, color: isRuleMode ? COLORS.SUB : COLORS.TEXT }}>
                {isRuleMode ? '간이 검증(규칙)' : 'AI 검증'}
              </span>
            </div>
            {items.length > 0 ? (
              <>
                {/* 인라인 해소 — 되돌리지 않고 그 자리에서 확인(K1) */}
                {items.map((it, i) => (
                  <div key={i} className="rounded-xl p-2.5 space-y-2" style={{ background: COLORS.CARD }}>
                    <p className="text-xs font-medium" style={{ color: COLORS.KB_GRAY }}>{it.question}</p>
                    <div className="flex flex-wrap gap-1.5">
                      {it.type === 'household' ? (
                        <>
                          <ChoiceBtn label={`${householdLabel(it.optionA)}가 맞아요`} onClick={() => acceptPair([it.optionA, it.optionB!])} />
                          <ChoiceBtn label={`${householdLabel(it.optionB!)}로 바꿀게요`} primary onClick={() => changeHousehold(it.optionB!)} />
                        </>
                      ) : it.type === 'intra' ? (
                        <ChoiceBtn label="의도한 게 맞아요 (둘 다)" onClick={() => acceptPair([it.optionA])} />
                      ) : (
                        <>
                          <ChoiceBtn label={`「${it.optionA}」`} onClick={() => removeNote(it.optionB!)} />
                          <ChoiceBtn label={`「${it.optionB}」`} onClick={() => removeNote(it.optionA)} />
                          {it.allowBoth && <ChoiceBtn label="둘 다 맞아요" onClick={() => acceptPair([it.optionA, it.optionB!])} />}
                        </>
                      )}
                    </div>
                  </div>
                ))}
                <p className="text-[11px]" style={{ color: COLORS.SUB }}>정할 때까지 자유입력은 동네 추천에 반영하지 않아요</p>
                <button onClick={() => dispatch({ type: 'NAVIGATE', screen: 'SC-02' })}
                  className="text-[11px] underline" style={{ color: COLORS.SUB }}>
                  문진에서 직접 고치기
                </button>
              </>
            ) : (axisCards.length > 0 || renewalPct != null || situations.length > 0) ? (
              <div className="space-y-2">
                {/* 원문 인용은 여기 헤더에서 1회만(전체). 카드 안에서는 반복 인용하지 않는다. */}
                {note.trim() && (
                  <p className="text-xs" style={{ color: COLORS.KB_GRAY }}>
                    남기신 말: <span className="italic" style={{ color: COLORS.SUB }}>“{note.length > 60 ? note.slice(0, 60) + '…' : note}”</span>
                  </p>
                )}
                <p className="text-[11px]" style={{ color: COLORS.SUB }}>승인한 것만 동네 추천에 실려요. (거절·확인 대기는 반영 안 함)</p>
                {/* ① 인상률 제안 — 별도 형태(숫자 확정), 맨 위 */}
                {renewalPct != null && (
                  <RenewalCard pct={renewalPct} ctype={contract.type} deposit={contract.deposit} monthly={contract.monthlyRent}
                    state={cardState('renewal')}
                    onApprove={() => approve('renewal')} onReject={() => reject('renewal')} onUndo={() => undo('renewal')} />
                )}
                {/* ①-b 갱신 상황 카드 — 권리 안내(무게 다름). 근거=결정표 원문. 인상률 아래·4축 위 */}
                {situations.map(sid => (
                  <SituationCard key={sid}
                    evidence={sitEvidence[sid] || ''}
                    guidance={RENEWAL_SITUATION_INFO[sid]?.guidance || ''}
                    citation={RENEWAL_SITUATION_INFO[sid]?.citation || ''}
                    state={cardState('sit:' + sid)}
                    onApprove={() => approve('sit:' + sid)} onReject={() => reject('sit:' + sid)} onUndo={() => undo('sit:' + sid)} />
                ))}
                {/* 전환 감액분 후속 입력 — jeonse_to_monthly 승인 시에만. 미입력이면 안내만(금액 미계산) */}
                {situations.includes('jeonse_to_monthly') && approved.has('sit:jeonse_to_monthly') && (
                  <div className="rounded-xl p-3" style={{ background: COLORS.CARD, border: `1.5px solid ${COLORS.KB_YELLOW}`, borderLeft: `4px solid ${COLORS.KB_GRAY}` }}>
                    <p className="text-sm font-semibold" style={{ color: COLORS.KB_GRAY }}>보증금을 얼마나 월세로 돌리자고 하나요?</p>
                    <div className="flex items-center gap-2 mt-1.5">
                      <input type="number" inputMode="numeric" min={0} value={convAmount}
                        onChange={e => setConvAmount(e.target.value)} placeholder="예: 10000"
                        className="w-28 px-3 py-2 rounded-xl border border-border bg-card text-foreground text-center" />
                      <span className="text-sm text-muted-foreground">만원</span>
                    </div>
                    <p className="text-[11px] mt-1.5" style={{ color: COLORS.SUB }}>비우면 안내만 하고 금액은 계산하지 않아요.</p>
                  </div>
                )}
                {/* 직접 추론 카드 */}
                {directCards.map(c => (
                  <ProposalCard key={c.axis} icon={AXIS_UI[c.axis]?.icon ?? '•'} title={AXIS_UI[c.axis]?.label ?? c.axis}
                    rationale={cardRationale(note, c.axis, c.direction)} state={cardState(c.axis)}
                    onApprove={() => approve(c.axis)} onReject={() => reject(c.axis)} onUndo={() => undo(c.axis)} />
                ))}
                {/* 확장 추론 — 접기(펼쳐서 개별 승인해야 반영, '모두 반영'에 안 걸림) */}
                {extCards.length > 0 && (
                  showExt ? (
                    extCards.map(c => (
                      <ProposalCard key={c.axis} icon={AXIS_UI[c.axis]?.icon ?? '•'} title={AXIS_UI[c.axis]?.label ?? c.axis}
                        rationale={cardRationale(note, c.axis, c.direction)} state={cardState(c.axis)} extended
                        onApprove={() => approve(c.axis)} onReject={() => reject(c.axis)} onUndo={() => undo(c.axis)} />
                    ))
                  ) : (
                    <button onClick={() => setShowExt(true)} className="text-xs underline w-full text-left" style={{ color: COLORS.SUB }}>
                      + 관련 제안 {extCards.length}개 ▾
                    </button>
                  )
                )}
                {(directCards.length > 0 || renewalPct != null) && (
                  <button onClick={approveAllDirect} className="text-[11px] underline" style={{ color: COLORS.KB_GRAY }}>
                    위 제안 모두 반영 (접힌 건 펼쳐서 개별 승인)
                  </button>
                )}
              </div>
            ) : (
              <p className="text-xs" style={{ color: COLORS.SUB }}>특별히 반영할 신호는 없었어요.</p>
            )}
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
            {/* 본인 진술 — 상충 미해결(held)이면 회색 + '확인 대기', 화살표(→ …) 효과는 확정 전 숨김(K3) */}
            {stated.map((s, i) => {
              const base = held ? s.label.split('→')[0].trim() : s.label;
              return held
                ? (
                  <span key={`st${i}`} className="inline-flex items-center gap-1 px-3 py-2 rounded-full border text-sm"
                    style={{ borderColor: COLORS.BORDER, background: '#00000006', color: COLORS.SUB }}>
                    {base}
                    <span className="text-[10px] px-1.5 py-0.5 rounded-full" style={{ background: '#00000010', color: COLORS.SUB }}>확인 대기</span>
                  </span>
                )
                : <FactTag key={`st${i}`} label={s.label} note="직접 말씀하신 내용" />;
            })}
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

      <div className="px-5 pb-8 pt-3 space-y-2">
        {/* 승인한 것만 실린다. 상충 미해결 중엔 그냥 진행(카드 미노출). */}
        {items.length === 0 && (axisCards.length > 0 || renewalPct != null) ? (
          <PrimaryBtn onClick={() => { applyAndCompare(); setApplied(true); }}>
            {approved.size > 0 ? `승인 ${approved.size}건 반영하고 비교하기 →` : '반영 없이 비교하기 →'}
          </PrimaryBtn>
        ) : (
          <PrimaryBtn onClick={() => dispatch({ type: 'NAVIGATE', screen: 'SC-03' })}>이대로 비교하기 →</PrimaryBtn>
        )}
      </div>
    </MobileShell>
  );
}

// C: 축 제안 카드 — 확인 대기(점선·회색) / 승인(솔리드) / 거절(흐림·취소선, 되돌리기 가능)
function ProposalCard({ icon, title, rationale, state, extended, onApprove, onReject, onUndo }: {
  icon: string; title: string; rationale: string; state: 'pending' | 'approved' | 'rejected';
  extended?: boolean; onApprove: () => void; onReject: () => void; onUndo: () => void;
}) {
  const border = state === 'approved' ? COLORS.KB_YELLOW : state === 'rejected' ? COLORS.BORDER : COLORS.SUB;
  return (
    <div className="rounded-xl p-3" style={{
      background: COLORS.CARD,
      border: `${state === 'pending' ? '1.5px dashed' : '1.5px solid'} ${border}`,
      opacity: state === 'rejected' ? 0.5 : 1,
    }}>
      <div className="flex items-center gap-1.5">
        <span className="text-sm">{icon}</span>
        <span className="text-sm font-bold" style={{ color: COLORS.KB_GRAY, textDecoration: state === 'rejected' ? 'line-through' : 'none' }}>{title}</span>
        {extended && <span className="text-[9px] px-1 py-0.5 rounded" style={{ background: '#00000010', color: COLORS.SUB }}>관련 제안</span>}
      </div>
      <p className="text-xs mt-1" style={{ color: COLORS.SUB, textDecoration: state === 'rejected' ? 'line-through' : 'none' }}>{rationale}</p>
      <div className="flex gap-1.5 mt-2">
        {state === 'pending' ? (
          <>
            <ChoiceBtn label="반영" primary onClick={onApprove} />
            <ChoiceBtn label="아니요" onClick={onReject} />
          </>
        ) : (
          <>
            <span className="text-[11px] font-semibold px-2 py-1" style={{ color: state === 'approved' ? COLORS.KB_GRAY : COLORS.SUB }}>
              {state === 'approved' ? '✓ 반영' : '반영 안 함'}
            </span>
            <ChoiceBtn label="되돌리기" onClick={onUndo} />
          </>
        )}
      </div>
    </div>
  );
}

// C①: 인상률 카드 — 4축과 다른 형태(숫자 확정 + 상한 판정 프리뷰 + 적용 대상·산식)
function RenewalCard({ pct, ctype, deposit, monthly, state, onApprove, onReject, onUndo }: {
  pct: number; ctype: string; deposit: number; monthly: number;
  state: 'pending' | 'approved' | 'rejected'; onApprove: () => void; onReject: () => void; onUndo: () => void;
}) {
  const over = pct > 5;
  const cap = Math.min(pct, 5);                 // 실제 적용률 = min(요구%, 법정 5%)
  const isJeonse = ctype === '전세';
  const target = isJeonse ? '보증금' : '월세';   // 적용 대상: 전세=보증금 / 월세=차임
  const before = isJeonse ? deposit : monthly;
  const after = Math.round(before * (1 + cap / 100)); // 표시용 재계산(계산 로직 아님 — 근거 노출)
  const man = (v: number) => `${Math.round(v / 10_000).toLocaleString()}만`;
  const border = state === 'approved' ? COLORS.KB_YELLOW : state === 'rejected' ? COLORS.BORDER : COLORS.SUB;
  return (
    <div className="rounded-xl p-3" style={{
      background: over ? '#FDECEC' : COLORS.CARD,
      border: `${state === 'pending' ? '1.5px dashed' : '1.5px solid'} ${border}`,
      opacity: state === 'rejected' ? 0.5 : 1,
    }}>
      <p className="text-sm font-bold" style={{ color: COLORS.KB_GRAY, textDecoration: state === 'rejected' ? 'line-through' : 'none' }}>
        💰 집주인이 {target}{eulReul(target)} {pct}% 올려달래요
      </p>
      <p className="text-xs mt-1" style={{ color: COLORS.SUB }}>
        {over ? `⚠️ 법정 상한 5%를 넘어 5%로 계산돼요.` : `법정 상한(5%) 이내예요.`} 이 값으로 갱신을 계산할까요?
      </p>
      <p className="text-[11px] mt-1 font-medium" style={{ color: COLORS.KB_GRAY }}>
        {target} {man(before)} → {cap}% → {man(after)}
      </p>
      <div className="flex gap-1.5 mt-2">
        {state === 'pending' ? (
          <>
            <ChoiceBtn label="반영" primary onClick={onApprove} />
            <ChoiceBtn label="아니요" onClick={onReject} />
          </>
        ) : (
          <>
            <span className="text-[11px] font-semibold px-2 py-1" style={{ color: state === 'approved' ? COLORS.KB_GRAY : COLORS.SUB }}>
              {state === 'approved' ? '✓ 반영' : '반영 안 함'}
            </span>
            <ChoiceBtn label="되돌리기" onClick={onUndo} />
          </>
        )}
      </div>
    </div>
  );
}

// 갱신 상황 카드 — 권리 안내(4축과 무게 다름: 좌측 굵은 바 + '근거 확인' 배지). guidance/citation은 결정표 원문.
function SituationCard({ evidence, guidance, citation, state, onApprove, onReject, onUndo }: {
  evidence: string; guidance: string; citation: string;
  state: 'pending' | 'approved' | 'rejected'; onApprove: () => void; onReject: () => void; onUndo: () => void;
}) {
  const border = state === 'approved' ? COLORS.KB_YELLOW : state === 'rejected' ? COLORS.BORDER : COLORS.SUB;
  const strike = state === 'rejected' ? 'line-through' : 'none';
  return (
    <div className="rounded-xl p-3" style={{
      background: COLORS.CARD,
      border: `${state === 'pending' ? '1.5px dashed' : '1.5px solid'} ${border}`,
      borderLeft: `4px solid ${COLORS.KB_GRAY}`,  // 권리 안내 구분(좌측 굵은 바)
      opacity: state === 'rejected' ? 0.5 : 1,
    }}>
      <div className="flex items-center gap-1.5 mb-1">
        <span className="text-[9px] px-1.5 py-0.5 rounded-full font-semibold" style={{ background: COLORS.KB_GRAY, color: '#fff' }}>근거 확인</span>
      </div>
      {evidence && <p className="text-xs" style={{ color: COLORS.KB_GRAY, textDecoration: strike }}>“{evidence}”라고 하셨어요.</p>}
      <p className="text-sm font-medium mt-1" style={{ color: COLORS.KB_GRAY, textDecoration: strike }}>→ {guidance}</p>
      {citation && <p className="text-[11px] mt-1" style={{ color: COLORS.SUB }}>{citation}</p>}
      <div className="flex gap-1.5 mt-2">
        {state === 'pending' ? (
          <>
            <ChoiceBtn label="반영" primary onClick={onApprove} />
            <ChoiceBtn label="아니요" onClick={onReject} />
          </>
        ) : (
          <>
            <span className="text-[11px] font-semibold px-2 py-1" style={{ color: state === 'approved' ? COLORS.KB_GRAY : COLORS.SUB }}>
              {state === 'approved' ? '✓ 반영' : '반영 안 함'}
            </span>
            <ChoiceBtn label="되돌리기" onClick={onUndo} />
          </>
        )}
      </div>
    </div>
  );
}

// 인라인 해소 선택 버튼(K1)
function ChoiceBtn({ label, onClick, primary = false }: { label: string; onClick: () => void; primary?: boolean }) {
  return (
    <button onClick={onClick}
      className="text-xs font-semibold px-3 py-2 rounded-xl border active:scale-95 transition-transform"
      style={primary
        ? { background: COLORS.KB_YELLOW, color: COLORS.TEXT, borderColor: COLORS.KB_YELLOW }
        : { background: COLORS.CARD, color: COLORS.KB_GRAY, borderColor: COLORS.BORDER }}>
      {label}
    </button>
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
