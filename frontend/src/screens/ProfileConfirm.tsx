import React, { useEffect, useState } from 'react';
import { useApp } from '../store';
import { COLORS } from '../theme';
import { MobileShell, PrimaryBtn, DdayBar } from '../components/ui';
import { formatAmount } from '../utils/format';
import { api } from '../api/client';
import type { PersonaProfile, ClarifyResult } from '../api/types';

function householdLabel(h: string) {
  return h === '1인' ? '1인 가구' : h === '신혼' ? '신혼 가구' : '자녀 가구';
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
  }, [contract, finance, acceptedPairs]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!contract || !finance) return null;

  const items = validation?.conflictItems ?? [];
  const noteSignals = validation?.noteSignals ?? [];
  const hasNote = !!contract.note?.trim();
  const isRuleMode = validation?.mode === 'rule';
  const held = !!validation?.held;
  const hasAdjust = !held && !!validation?.weightAdjust && Object.keys(validation.weightAdjust).length > 0;

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

  // HITL 확정: 상충이 없을 때만, 검증이 해석한 조정을 이 시점에 noteAdjust에 반영(확정 전 미반영, B1·J2).
  function applyAndCompare() {
    if (hasAdjust) {
      dispatch({ type: 'SET_CONTRACT', contract: { ...contract!, noteAdjust: validation!.weightAdjust! } });
    }
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
            ) : noteSignals.length > 0 ? (
              <>
                <div className="flex flex-wrap gap-1.5">
                  {noteSignals.map((s, i) => (
                    <span key={i} className="text-[11px] px-2 py-0.5 rounded-full" style={{ background: '#00000008', color: COLORS.SUB }}>{s}</span>
                  ))}
                </div>
                {hasAdjust && (
                  <p className="text-[11px]" style={{ color: applied ? COLORS.MINT : COLORS.SUB }}>
                    {applied ? '✓ 동네 추천에 반영했어요' : '아래 [반영하고 비교]를 누르면 동네 추천에 실려요'}
                  </p>
                )}
              </>
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
        {/* 상충 없고 반영할 신호가 있으면 HITL 확정 버튼(이때만 noteAdjust 반영). 그 외엔 그냥 진행. */}
        {items.length === 0 && hasAdjust ? (
          <>
            <PrimaryBtn onClick={() => { applyAndCompare(); setApplied(true); }}>반영하고 비교하기 →</PrimaryBtn>
            <button onClick={() => dispatch({ type: 'NAVIGATE', screen: 'SC-03' })}
              className="w-full text-center text-xs text-muted-foreground py-1">반영 없이 비교만 할게요</button>
          </>
        ) : (
          <PrimaryBtn onClick={() => dispatch({ type: 'NAVIGATE', screen: 'SC-03' })}>이대로 비교하기 →</PrimaryBtn>
        )}
      </div>
    </MobileShell>
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
