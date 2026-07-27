import React, { useState, useEffect } from 'react';
import { useApp } from '../store';
import { COLORS } from '../theme';
import {
  MobileShell, DdayBar, BackBtn,
  PrimaryBtn, GhostBtn, SelectCard, AmountInput
} from '../components/ui';
import { api } from '../api/client';
import { formatDday, formatNoticeDeadline } from '../utils/format';
import type { ContractType, RenewalUsed, Household, FirstHome, HousingType, ClarifyResult } from '../api/types';

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
  const [housingType, setHousingType] = useState<HousingType>(state.contract?.housingType || '아파트');
  const [preferredArea, setPreferredArea] = useState<string>(state.contract?.preferredArea || '');
  const [note, setNote] = useState<string>('');
  const [interp, setInterp] = useState<ClarifyResult | null>(null);
  // 확정된 자유입력 누적(반영한 내용). 각 항목: {말한 것, 해석 신호들}
  const [reflected, setReflected] = useState<{ text: string; signals: string[] }[]>(
    state.contract?.note ? [{ text: state.contract.note, signals: [] }] : []
  );
  const [annualIncome, setAnnualIncome] = useState(state.finance?.annualIncome || 0);
  const [ownCapital, setOwnCapital] = useState(state.finance?.ownCapital || 0);
  const [household, setHousehold] = useState<Household>(state.finance?.household || '1인');
  const [firstHome, setFirstHome] = useState<FirstHome>(state.finance?.firstHome || '모름');
  const [under35, setUnder35] = useState<boolean>(state.finance?.under35 ?? false);

  // 자유입력 → AI 해석(디바운스). 세대유형은 아직 입력 전일 수 있어 현재 household 상태로 해석.
  useEffect(() => {
    if (!note.trim()) { setInterp(null); return; }
    const t = setTimeout(() => {
      api.clarify(
        { type: contractType, deposit: 0, monthlyRent: 0, expiryDate: '', renewalUsed, housingType, note },
        { annualIncome: 0, ownCapital: 0, household, firstHome, under35 },
      ).then(setInterp).catch(() => setInterp(null));
    }, 400);
    return () => clearTimeout(t);
  }, [note]); // eslint-disable-line react-hooks/exhaustive-deps

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
        note: [...reflected.map(r => r.text), note.trim()].filter(Boolean).join(' '),
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

  const dday = expiryDate ? formatDday(expiryDate) : undefined;
  const noticeLeft = expiryDate ? formatDday(formatNoticeDeadline(expiryDate, 2).toISOString()) : undefined;

  return (
    <MobileShell>
      {expiryDate && <DdayBar dday={dday} noticeDaysLeft={noticeLeft} />}

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
                더 알려주고 싶은 것 <span className="text-xs text-muted-foreground">(선택 — 없어도 됩니다)</span>
              </div>
              <textarea
                value={note}
                onChange={e => setNote(e.target.value)}
                rows={2}
                placeholder="예: 재택근무예요"
                className="w-full rounded-2xl border px-4 py-3 text-sm resize-none outline-none"
                style={{ borderColor: COLORS.BORDER, background: COLORS.CARD, color: COLORS.TEXT }}
              />
              {/* 예시 칩 — 탭하면 채워지고 바로 AI 해석(타이핑 없이 체험) */}
              <div className="flex flex-wrap gap-1.5 mt-2">
                {['재택근무예요', '반려동물이 있어요', '아이 학교가 중요해요', '부모님 근처에 살고 싶어요'].map(ex => (
                  <button key={ex} onClick={() => setNote(ex)}
                    className="text-xs px-3 py-1.5 rounded-full border"
                    style={{ borderColor: COLORS.BORDER, background: COLORS.CARD, color: COLORS.SUB }}>
                    {ex}
                  </button>
                ))}
              </div>

              {/* AI 해석 카드 (인라인, 모달 아님) */}
              {note.trim() && interp && (
                <div className="mt-3 rounded-2xl border p-3.5 space-y-2 animate-[fadeIn_.2s_ease]"
                  style={{ borderColor: COLORS.KB_YELLOW, background: COLORS.YELLOW_SURFACE }}>
                  <div className="flex items-start gap-2">
                    <span className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
                      style={{ background: COLORS.KB_YELLOW, color: COLORS.TEXT }}>AI</span>
                    <p className="text-sm leading-snug" style={{ color: COLORS.TEXT }}>
                      {(interp.noteSignals?.length ?? 0) > 0
                        ? '이렇게 이해했어요 — 동네 추천에 반영할까요?'
                        : '입력을 확인했어요. 이대로 반영할까요?'}
                    </p>
                  </div>
                  {(interp.noteSignals ?? []).length > 0 && (
                    <div className="flex flex-wrap gap-1.5 pl-8">
                      {interp.noteSignals!.map((s, i) => (
                        <span key={i} className="text-[11px] px-2 py-0.5 rounded-full"
                          style={{ background: '#00000008', color: COLORS.SUB }}>{s}</span>
                      ))}
                    </div>
                  )}
                  {(interp.conflicts ?? []).map((c, i) => (
                    <p key={i} className="text-xs pl-8" style={{ color: COLORS.SUB }}>💬 {c}</p>
                  ))}
                  <div className="flex gap-2 pl-8 pt-0.5">
                    <button onClick={() => {
                      setReflected(r => [...r, { text: note.trim(), signals: interp?.noteSignals ?? [] }]);
                      setNote(''); setInterp(null);
                    }}
                      className="flex-1 text-xs font-semibold py-2 rounded-xl"
                      style={{ background: COLORS.KB_YELLOW, color: COLORS.TEXT }}>
                      네, 맞아요
                    </button>
                    <button onClick={() => { setNote(''); setInterp(null); }}
                      className="flex-1 text-xs font-semibold py-2 rounded-xl border"
                      style={{ borderColor: COLORS.BORDER, color: COLORS.SUB, background: COLORS.CARD }}>
                      아니요, 그대로
                    </button>
                  </div>
                </div>
              )}

              {/* 반영한 내용 — 확정 누적, X로 해제 */}
              {reflected.length > 0 && (
                <div className="mt-3">
                  <p className="text-xs font-medium mb-1.5" style={{ color: COLORS.SUB }}>반영한 내용</p>
                  <div className="flex flex-wrap gap-1.5">
                    {reflected.flatMap((r, ri) =>
                      (r.signals.length ? r.signals : [r.text]).map((s, si) => (
                        <span key={`${ri}-${si}`} className="inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded-full"
                          style={{ background: COLORS.YELLOW_SURFACE, color: COLORS.TEXT }}>
                          ✓ {s}
                          <button onClick={() => setReflected(list => list.filter((_, i) => i !== ri))}
                            className="opacity-60 hover:opacity-100" aria-label="해제">✕</button>
                        </span>
                      ))
                    )}
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
