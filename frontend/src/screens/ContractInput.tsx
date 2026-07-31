import React, { useState } from 'react';
import { useApp } from '../store';
import { COLORS } from '../theme';
import {
  MobileShell, BackBtn,
  PrimaryBtn, GhostBtn, SelectCard, AmountInput
} from '../components/ui';
import { api } from '../api/client';
import type { ContractType, RenewalUsed, Household, FirstHome, HousingType } from '../api/types';

// ─── 스텝 정의 ─────────────────────────────────────────────────────────────
type StepId = 'type' | 'deposit' | 'rent' | 'expiry' | 'renewal' | 'finance';

interface StepDef { id: StepId; title: string }

function buildSteps(type: ContractType): StepDef[] {
  return [
    { id: 'type',    title: '계약 유형' },
    { id: 'deposit', title: '보증금' },
    ...(type === '월세' ? [{ id: 'rent' as StepId, title: '월세액' }] : []),
    { id: 'expiry',  title: '만기일' },
    { id: 'renewal', title: '갱신청구권' },
    { id: 'finance', title: '소득·자산' },
  ];
}

// ─── 소득·자산 구간 ────────────────────────────────────────────────────────
const INCOME_RANGES = [
  { label: '3천 미만', value: 25_000_000 },
  { label: '3~4천',   value: 35_000_000 },
  { label: '4~5천',   value: 45_000_000 },
  { label: '5~6천',   value: 55_000_000 },
  { label: '6~8천',   value: 70_000_000 },
  { label: '8천 이상', value: 90_000_000 },
];

const CAPITAL_RANGES = [
  { label: '1천 미만',  value: 5_000_000 },
  { label: '1~3천',    value: 20_000_000 },
  { label: '3~5천',    value: 40_000_000 },
  { label: '5천~1억',  value: 75_000_000 },
  { label: '1억~2억',  value: 150_000_000 },
  { label: '2억 이상', value: 250_000_000 },
];

// 프리셋 칩 목록 + 상호배타쌍(K2). **우리가 만든 칩끼리의 관계**라 키워드 추론이 아님(오탐 없음).
// 자유 텍스트 입력에는 이 판정을 적용하지 않는다 — 의미 충돌은 최종 AI 검증에 맡긴다.
const PRESET_CHIPS = ['재택근무예요', '매일 통근해요', '조용한 동네가 좋아요', '번화가가 가까웠으면', '반려동물이 있어요', '아이 학교가 중요해요'];
const EXCLUSIVE_PAIRS: [string, string][] = [
  ['재택근무예요', '매일 통근해요'],
  ['조용한 동네가 좋아요', '번화가가 가까웠으면'],
];

export default function ContractInput() {
  const { state, dispatch } = useApp();

  const [contractType, setContractType] = useState<ContractType>(state.contract?.type || '전세');
  const [stepIdx, setStepIdx] = useState(0);

  const [deposit, setDeposit] = useState(
    state.contract ? String(Math.round(state.contract.deposit / 10_000)) : ''
  );
  const [monthlyRent, setMonthlyRent] = useState(
    state.contract ? String(Math.round(state.contract.monthlyRent / 10_000)) : ''
  );
  const [expiryDate, setExpiryDate] = useState(state.contract?.expiryDate || '');
  const [renewalUsed, setRenewalUsed] = useState<RenewalUsed>(state.contract?.renewalUsed || '미사용');
  // 집주인이 요구한 인상률(선택). 빈값=미입력(null) → 기존 5% 상한 동작 불변. 자유입력으로도 잡히지만 여기서 직접 입력도 가능.
  const [renewalAskPct, setRenewalAskPct] = useState<string>(
    state.contract?.renewalAskPct != null ? String(state.contract.renewalAskPct) : ''
  );
  const [housingType, setHousingType] = useState<HousingType>(state.contract?.housingType || '아파트');
  const [preferredArea, setPreferredArea] = useState<string>(state.contract?.preferredArea || '');
  const [note, setNote] = useState<string>('');
  // 누적한 자유입력(반영한 내용). 문진 중엔 '판단' 없이 텍스트만 쌓는다 — 상충 검증은 최종 프로필(SC-14) 1회.
  const [reflected, setReflected] = useState<{ text: string }[]>(
    state.contract?.note ? state.contract.note.split(' · ').filter(Boolean).map(t => ({ text: t })) : []
  );
  const [annualIncome, setAnnualIncome] = useState(state.finance?.annualIncome || 0);
  const [ownCapital, setOwnCapital] = useState(state.finance?.ownCapital || 0);
  const [household, setHousehold] = useState<Household>(state.finance?.household || '1인');
  const [firstHome, setFirstHome] = useState<FirstHome>(state.finance?.firstHome || '모름');
  const [under35, setUnder35] = useState<boolean>(state.finance?.under35 ?? false);

  const [swap, setSwap] = useState<{ chip: string; partner: string } | null>(null);

  // 자유입력 등록 — [추가]/엔터로 명시 등록(문진 중엔 판단 안 함, 누적만). 검증은 SC-14 최종 프로필에서 1회.
  function addNote(text: string) {
    const t = text.trim();
    if (!t) return;
    setReflected(r => (r.some(x => x.text === t) ? r : [...r, { text: t }]));
    api.hitl('applied', [t], t);  // 관측: 사용자가 무엇을 등록했는지(확정 반영은 SC-14)
    setNote('');
  }

  // 프리셋 칩 등록 — 이미 담긴 칩과 배타 관계면 교체 제안(K2). 자유 텍스트에는 미적용.
  function addPreset(chip: string) {
    const pair = EXCLUSIVE_PAIRS.find(([a, b]) => (chip === a || chip === b) && reflected.some(r => r.text === (chip === a ? b : a)));
    if (pair) { setSwap({ chip, partner: chip === pair[0] ? pair[1] : pair[0] }); return; }
    addNote(chip);
  }

  // 유형 변경 시 스텝 배열 재계산, 현재 stepIdx 클램프
  const steps = buildSteps(contractType);
  const currentStep = steps[stepIdx];
  const total = steps.length;

  function handleTypeChange(t: ContractType) {
    setContractType(t);
    // 유형 변경 시 스텝 배열이 바뀌어도 'type' 스텝에 있으면 그대로
    setStepIdx(0);
  }

  function canNext(): boolean {
    switch (currentStep.id) {
      case 'type':    return true;
      case 'deposit': return deposit.length > 0;
      case 'rent':    return monthlyRent.length > 0;
      case 'expiry':  return expiryDate.length > 0;
      case 'renewal': return true;
      case 'finance': return annualIncome > 0 && ownCapital > 0;
    }
  }

  function next() {
    if (stepIdx < steps.length - 1) { setStepIdx(i => i + 1); return; }
    // 자유입력은 누적만(텍스트). 해석·상충 검증·반영(noteAdjust)은 SC-14 최종 프로필에서 1회.
    // 미입력 상태로 남은 textarea 내용도 함께 담는다(등록 안 눌렀어도 유실 방지).
    const notes = [...reflected.map(r => r.text), note.trim()].filter(Boolean);
    dispatch({
      type: 'SET_CONTRACT',
      contract: {
        type: contractType,
        deposit: parseInt(deposit || '0') * 10_000,
        monthlyRent: contractType === '월세' ? parseInt(monthlyRent || '0') * 10_000 : 0,
        expiryDate,
        renewalUsed,
        housingType,
        preferredArea,
        note: notes.join(' · '),
        noteAdjust: {},  // 확정 전엔 비움 — SC-14에서 검증 후 HITL 확정 시 채워짐(B1·J2)
        renewalAskPct: renewalAskPct.trim() !== '' ? parseInt(renewalAskPct, 10) : null,  // 미입력=null → 5% 상한 불변
      },
    });
    dispatch({
      type: 'SET_FINANCE',
      finance: { annualIncome, ownCapital, household, firstHome, under35 },
    });
    dispatch({ type: 'NAVIGATE', screen: 'SC-12' });
  }

  function back() {
    if (stepIdx > 0) setStepIdx(i => i - 1);
    else dispatch({ type: 'NAVIGATE', screen: 'SC-01' });
  }

  // §3: 만기 배너는 만기일 '확정 이후'(문진 완료·비교 존재) 화면에서만. 문진 진행 중엔 숨김(잔존값 노출 금지).
  return (
    <MobileShell>
      {/* 스텝 진행바 — 현재 index / steps.length (하드코딩 없음) */}
      <div className="flex items-center px-4 pt-2 pb-2">
        <BackBtn onClick={back} />
        <div className="flex-1 flex items-center gap-2 px-2">
          <div className="flex-1 h-1.5 bg-border rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{ width: `${((stepIdx + 1) / total) * 100}%`, background: COLORS.KB_YELLOW }}
            />
          </div>
          <span className="text-xs text-muted-foreground font-medium whitespace-nowrap">
            {stepIdx + 1}/{total}
          </span>
        </div>
      </div>

      <div className="flex-1 px-5 py-4 overflow-y-auto">
        {currentStep.id === 'type' && (
          <StepView title="어떤 계약인가요?">
            <div className="grid grid-cols-2 gap-3">
              <SelectCard selected={contractType === '전세'} onClick={() => handleTypeChange('전세')}>
                <div className="text-2xl mb-1">🏦</div>
                <div className="font-semibold">전세</div>
                <div className="text-xs text-muted-foreground mt-0.5">보증금만 내는 방식</div>
              </SelectCard>
              <SelectCard selected={contractType === '월세'} onClick={() => handleTypeChange('월세')}>
                <div className="text-2xl mb-1">🗓</div>
                <div className="font-semibold">월세</div>
                <div className="text-xs text-muted-foreground mt-0.5">보증금+월세 방식</div>
              </SelectCard>
            </div>
            <div className="mt-5">
              <div className="text-sm font-medium mb-2">주택 유형</div>
              <div className="grid grid-cols-2 gap-3">
                <SelectCard selected={housingType === '아파트'} onClick={() => setHousingType('아파트')}>
                  <div className="text-2xl mb-1">🏢</div>
                  <div className="font-semibold">아파트</div>
                </SelectCard>
                <SelectCard selected={housingType === '연립다세대'} onClick={() => setHousingType('연립다세대')}>
                  <div className="text-2xl mb-1">🏠</div>
                  <div className="font-semibold">원룸·투룸·빌라</div>
                  <div className="text-xs text-muted-foreground mt-0.5">연립·다세대</div>
                </SelectCard>
              </div>
            </div>
            <div className="mt-5">
              <div className="text-sm font-medium mb-2">
                선호 지역 <span className="text-xs text-muted-foreground">(동네 후보를 이 근처에서)</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {['', '마포구', '은평구', '도봉구', '성북구', '노원구', '중랑구'].map(gu => (
                  <button
                    key={gu || 'any'}
                    onClick={() => setPreferredArea(gu)}
                    className="text-sm px-3 py-1.5 rounded-full border"
                    style={{
                      borderColor: preferredArea === gu ? COLORS.KB_YELLOW : COLORS.BORDER,
                      background: preferredArea === gu ? COLORS.YELLOW_SURFACE : COLORS.CARD,
                      color: preferredArea === gu ? COLORS.TEXT : COLORS.SUB,
                    }}
                  >
                    {gu || '상관없음'}
                  </button>
                ))}
              </div>
            </div>
            <div className="mt-5">
              <div className="text-sm font-medium mb-2">
                더 알려주고 싶은 것 <span className="text-xs text-muted-foreground">(선택 · 여러 개 추가 가능)</span>
              </div>
              <div className="flex gap-2">
                <input
                  value={note}
                  onChange={e => setNote(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addNote(note); } }}
                  placeholder="예: 재택근무예요 (엔터 또는 추가)"
                  className="flex-1 rounded-2xl border px-4 py-3 text-sm outline-none"
                  style={{ borderColor: COLORS.BORDER, background: COLORS.CARD, color: COLORS.TEXT }}
                />
                <button onClick={() => addNote(note)} disabled={!note.trim()}
                  className="px-4 rounded-2xl text-sm font-semibold shrink-0 disabled:opacity-40"
                  style={{ background: COLORS.KB_YELLOW, color: COLORS.TEXT }}>
                  추가
                </button>
              </div>
              {/* 예시 칩 — 탭하면 바로 담김(누적). 배타 칩이 이미 있으면 교체 제안(K2) */}
              <div className="flex flex-wrap gap-1.5 mt-2">
                {PRESET_CHIPS.map(ex => (
                  <button key={ex} onClick={() => addPreset(ex)} disabled={reflected.some(r => r.text === ex)}
                    className="text-xs px-3 py-1.5 rounded-full border disabled:opacity-40"
                    style={{ borderColor: COLORS.BORDER, background: COLORS.CARD, color: COLORS.SUB }}>
                    + {ex}
                  </button>
                ))}
              </div>

              {/* 배타 칩 교체 제안 — 자유 텍스트가 아니라 우리가 정의한 칩 관계라 오탐 없음 */}
              {swap && (
                <div className="mt-2 rounded-2xl border p-3 space-y-2" style={{ borderColor: COLORS.KB_YELLOW, background: COLORS.YELLOW_SURFACE }}>
                  <p className="text-xs" style={{ color: COLORS.TEXT }}>
                    '{swap.partner}'와 반대되는 내용이에요. 바꿀까요?
                  </p>
                  <div className="flex gap-2">
                    <button onClick={() => { setReflected(r => r.filter(x => x.text !== swap.partner)); addNote(swap.chip); setSwap(null); }}
                      className="flex-1 text-xs font-semibold py-2 rounded-xl" style={{ background: COLORS.KB_YELLOW, color: COLORS.TEXT }}>
                      바꾸기
                    </button>
                    <button onClick={() => { addNote(swap.chip); setSwap(null); }}
                      className="flex-1 text-xs font-semibold py-2 rounded-xl border" style={{ borderColor: COLORS.BORDER, color: COLORS.SUB, background: COLORS.CARD }}>
                      둘 다 담기
                    </button>
                  </div>
                </div>
              )}

              {/* 반영한 내용 — 누적, X로 해제. 상충 검증·해석은 다음 '당신의 프로필'(SC-14)에서 한 번에. */}
              {reflected.length > 0 && (
                <div className="mt-3">
                  <p className="text-xs font-medium mb-1.5" style={{ color: COLORS.SUB }}>
                    담아둔 내용 <span className="font-normal">— 프로필 단계에서 AI가 한 번에 확인해요</span>
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {reflected.map((r, ri) => (
                      <span key={ri} className="inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded-full"
                        style={{ background: COLORS.YELLOW_SURFACE, color: COLORS.TEXT }}>
                        ✓ {r.text}
                        <button onClick={() => setReflected(list => list.filter((_, i) => i !== ri))}
                          className="opacity-60 hover:opacity-100" aria-label="해제">✕</button>
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </StepView>
        )}

        {currentStep.id === 'deposit' && (
          <StepView title="보증금이 얼마인가요?">
            <AmountInput value={deposit} onChange={setDeposit} label="보증금 (만원)" placeholder="예: 32000" />
          </StepView>
        )}

        {currentStep.id === 'rent' && (
          <StepView title="월세액을 알려주세요">
            <AmountInput value={monthlyRent} onChange={setMonthlyRent} label="월세 (만원)" placeholder="예: 200" />
          </StepView>
        )}

        {currentStep.id === 'expiry' && (
          <StepView title="계약 만기일을 알려주세요">
            <div
              className="rounded-2xl border-2 px-4 py-3"
              style={{ borderColor: expiryDate ? COLORS.KB_YELLOW : COLORS.BORDER, background: '#F7F3EC' }}
            >
              <label className="text-xs text-muted-foreground">만기일</label>
              <input
                type="date"
                value={expiryDate}
                onChange={e => setExpiryDate(e.target.value)}
                className="w-full bg-transparent text-xl font-bold text-foreground outline-none mt-1"
                min={new Date().toISOString().split('T')[0]}
              />
            </div>
            <button className="text-xs text-muted-foreground underline mt-3">
              계약서에서 만기일 확인하는 법 →
            </button>
          </StepView>
        )}

        {currentStep.id === 'renewal' && (
          <StepView
            title="갱신청구권을 사용하셨나요?"
            sub="모르셔도 괜찮아요. 두 경우 모두 계산해드릴게요."
          >
            <div className="space-y-3">
              {([
                ['미사용', '아직 안 썼어요', '갱신 시 법정 상한 5% 적용'],
                ['사용',   '이미 썼어요',   '협의 필요, 계산에 반영'],
                ['모름',   '모르겠어요',    '두 경우 모두 계산해요'],
              ] as const).map(([val, label, sub]) => (
                <SelectCard key={val} selected={renewalUsed === val} onClick={() => setRenewalUsed(val)}>
                  <div className="font-semibold">{label}</div>
                  <div className="text-xs text-muted-foreground mt-0.5">{sub}</div>
                </SelectCard>
              ))}
            </div>
            {renewalUsed === '모름' && (
              <div className="mt-3 px-4 py-3 bg-muted rounded-2xl text-sm text-muted-foreground">
                괜찮아요, 두 경우 모두 계산해드릴게요 😊
              </div>
            )}
            {/* 집주인 요구 인상률(선택) — 비우면 법정 5% 상한으로 계산 */}
            <div className="mt-5">
              <p className="text-sm font-semibold mb-1">집주인이 인상률을 말했나요? <span className="text-xs font-normal text-muted-foreground">(선택)</span></p>
              <p className="text-xs text-muted-foreground mb-2">비워두면 법정 상한 5%로 계산해요. 상한을 넘겨 부르면 5% 기준으로 다시 계산해드려요.</p>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  inputMode="numeric"
                  min={0}
                  max={100}
                  value={renewalAskPct}
                  onChange={e => setRenewalAskPct(e.target.value)}
                  placeholder="예: 7"
                  className="w-24 px-3 py-2 rounded-xl border border-border bg-card text-foreground text-center"
                />
                <span className="text-sm text-muted-foreground">% 올려달래요</span>
              </div>
            </div>
          </StepView>
        )}

        {currentStep.id === 'finance' && (
          <StepView title="소득과 자산을 알려주세요" sub="대출 한도 추정에 사용해요. 저장되지 않아요.">
            <div className="space-y-5">
              <div>
                <p className="text-sm font-semibold mb-2">연소득 구간</p>
                <div className="grid grid-cols-3 gap-2">
                  {INCOME_RANGES.map(r => (
                    <button
                      key={r.label}
                      onClick={() => setAnnualIncome(r.value)}
                      className="py-2.5 rounded-xl text-sm font-medium border transition-colors"
                      style={{
                        borderColor: annualIncome === r.value ? COLORS.KB_YELLOW : COLORS.BORDER,
                        background:  annualIncome === r.value ? COLORS.YELLOW_SURFACE : COLORS.CARD,
                        color:       annualIncome === r.value ? COLORS.TEXT : COLORS.SUB,
                      }}
                    >
                      {r.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <p className="text-sm font-semibold mb-2">모은 돈 (보증금 외)</p>
                <div className="grid grid-cols-3 gap-2">
                  {CAPITAL_RANGES.map(r => (
                    <button
                      key={r.label}
                      onClick={() => setOwnCapital(r.value)}
                      className="py-2.5 rounded-xl text-sm font-medium border transition-colors"
                      style={{
                        borderColor: ownCapital === r.value ? COLORS.KB_YELLOW : COLORS.BORDER,
                        background:  ownCapital === r.value ? COLORS.YELLOW_SURFACE : COLORS.CARD,
                        color:       ownCapital === r.value ? COLORS.TEXT : COLORS.SUB,
                      }}
                    >
                      {r.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <p className="text-sm font-semibold mb-2">가구 형태</p>
                <div className="grid grid-cols-3 gap-2">
                  {(['1인', '신혼', '자녀'] as Household[]).map(h => (
                    <button
                      key={h}
                      onClick={() => setHousehold(h)}
                      className="py-2.5 rounded-xl text-sm font-medium border transition-colors"
                      style={{
                        borderColor: household === h ? COLORS.KB_YELLOW : COLORS.BORDER,
                        background:  household === h ? COLORS.YELLOW_SURFACE : COLORS.CARD,
                        color:       household === h ? COLORS.TEXT : COLORS.SUB,
                      }}
                    >
                      {h === '1인' ? '👤 1인' : h === '신혼' ? '💑 신혼' : '👨‍👩‍👧 자녀'}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <p className="text-sm font-semibold mb-2">생애최초 주택 구입인가요?</p>
                <div className="grid grid-cols-3 gap-2">
                  {(['예', '아니오', '모름'] as FirstHome[]).map(v => (
                    <button
                      key={v}
                      onClick={() => setFirstHome(v)}
                      className="py-2.5 rounded-xl text-sm font-medium border transition-colors"
                      style={{
                        borderColor: firstHome === v ? COLORS.KB_YELLOW : COLORS.BORDER,
                        background:  firstHome === v ? COLORS.YELLOW_SURFACE : COLORS.CARD,
                        color:       firstHome === v ? COLORS.TEXT : COLORS.SUB,
                      }}
                    >
                      {v}
                    </button>
                  ))}
                </div>
                <p className="text-xs text-muted-foreground mt-1">생애최초면 LTV·취득세 혜택을 반영해요</p>
              </div>

              <div>
                <p className="text-sm font-semibold mb-2">만 35세 미만인가요?</p>
                <div className="grid grid-cols-2 gap-2">
                  {([['예', true], ['아니오', false]] as const).map(([label, val]) => (
                    <button
                      key={label}
                      onClick={() => setUnder35(val)}
                      className="py-2.5 rounded-xl text-sm font-medium border transition-colors"
                      style={{
                        borderColor: under35 === val ? COLORS.KB_YELLOW : COLORS.BORDER,
                        background:  under35 === val ? COLORS.YELLOW_SURFACE : COLORS.CARD,
                        color:       under35 === val ? COLORS.TEXT : COLORS.SUB,
                      }}
                    >
                      {label}
                    </button>
                  ))}
                </div>
                <p className="text-xs text-muted-foreground mt-1">청년 전세대출(버팀목) 자격 확인용</p>
              </div>
            </div>
          </StepView>
        )}
      </div>

      <div className="px-5 pb-8 pt-3 space-y-3">
        <PrimaryBtn onClick={next} disabled={!canNext()}>
          {stepIdx < steps.length - 1 ? '다음 →' : '비교표 만들기'}
        </PrimaryBtn>
        <GhostBtn onClick={() => dispatch({ type: 'NAVIGATE', screen: 'SC-01' })} className="w-full text-center">
          나중에 할게요
        </GhostBtn>
      </div>
    </MobileShell>
  );
}

function StepView({ title, sub, children }: { title: string; sub?: string; children: React.ReactNode }) {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-foreground">{title}</h1>
        {sub && <p className="text-sm text-muted-foreground mt-1">{sub}</p>}
      </div>
      {children}
    </div>
  );
}
