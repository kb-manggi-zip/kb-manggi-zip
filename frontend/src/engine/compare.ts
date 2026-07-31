import { RULES } from './rules';
import { resolveRenewal } from './renewalCases';
import type { ContractInfo, FinanceInfo, CompareResponse, BranchResult, Household, FirstHome } from '../api/types';

// ⚠️ 백엔드 app/tools/compare.py 와 1:1 동치 (오차 0). 한쪽만 고치지 말 것.
//    수정 후: cd backend && TZ=UTC npx tsx scripts/gen_fixtures.mjs && pytest

// ── 대출 상환/한도 프리미티브 (backend/app/tools/lending_calc.py 미러) ──
function annuity(P: number, annualRate: number, years: number): number {
  if (P <= 0) return 0;
  const r = annualRate / 12, n = years * 12;
  if (r === 0) return P / n;
  return (P * r) / (1 - Math.pow(1 + r, -n));
}
function pvAnnuity(pmt: number, annualRate: number, years: number): number {
  if (pmt <= 0) return 0;
  const r = annualRate / 12, n = years * 12;
  if (r === 0) return pmt * n;
  return (pmt * (1 - Math.pow(1 + r, -n))) / r;
}
function solveMaxPrice(capital: number, ltv: number, dsrLimit: number, policyLimit: number, bankCap: number): number {
  const absCap = Math.min(dsrLimit, policyLimit + bankCap);
  const priceAbs = capital + absCap;
  const priceLtv = ltv >= 1 ? Infinity : capital / (1 - ltv);
  return Math.floor(Math.min(priceLtv, priceAbs)); // Python int() 절삭과 동치(양수)
}

// ── 정책대출 (backend/app/tools/policy_loans.py 미러) ──
function didimdol(income: number, household: Household, firstHome: FirstHome, netAsset: number) {
  const d = RULES.policyLoans.didimdol;
  let incomeCap: number, limit: number;
  if (household === '신혼') { incomeCap = d.income_cap.newlywed; limit = d.limit.newlywed_or_2child; }
  else if (household === '자녀') { incomeCap = d.income_cap.first_home_or_2child; limit = d.limit.newlywed_or_2child; }
  else if (firstHome === '예') { incomeCap = d.income_cap.first_home_or_2child; limit = d.limit.first_home; }
  else { incomeCap = d.income_cap.general; limit = d.limit.general; }
  const eligible = (!d.requires_no_house || true) && income <= incomeCap && netAsset <= d.net_asset_cap;
  return { eligible, limit: eligible ? limit : 0, rate: d.rate_min };
}
function buttimok(under35: boolean, income: number, deposit: number, netAsset: number) {
  const b = RULES.policyLoans.buttimok_youth;
  const age = under35 ? 30 : 99;
  const inAge = age >= b.ageMin && age <= b.ageMax;
  const eligible = inAge && income <= b.income_cap && deposit <= b.deposit_cap && netAsset <= b.net_asset_cap;
  let rate = b.rate_by_income[b.rate_by_income.length - 1].rate;
  for (const t of b.rate_by_income) { if (income <= t.upto) { rate = t.rate; break; } }
  return { eligible, limit: eligible ? b.limit : 0, rate };
}

// ── HUG 보증료율 (backend/app/tools/guarantee_hug.py 미러) ──
function guaranteeRate(deposit: number, houseType: string): number {
  const g = RULES.guaranteeHug;
  const band = deposit <= 90_000_000 ? 'under_90m' : deposit <= 200_000_000 ? 'm90_to_200m' : 'over_200m';
  return (g.hug_fee_rate as any)[band][houseType][g.default_debt_ratio];
}

// ── 중개보수 구간표 조회 (backend/app/tools/broker_fee.py 미러) ──
function brokerFee(amount: number, bands: typeof RULES.oneTime.brokerRateBands = RULES.oneTime.brokerRateBands): number {
  const band = bands.find(b => b.upto === null || amount < b.upto) ?? bands[bands.length - 1];
  const fee = amount * band.rate;
  return band.cap !== null ? Math.min(fee, band.cap) : fee;
}

// ── 취득세+지방교육세 구간 조회 (backend/app/tools/acquisition_tax.py 미러) ──
function acquisitionFee(price: number): number {
  const a = RULES.oneTime.acquisition;
  let base: number;
  if (price <= a.lowThreshold) base = a.lowRate;
  else if (price > a.highThreshold) base = a.highRate;
  else {
    const rawPercent = (price / 300_000_000) * 2 - 3;
    const roundedPercent = Math.round(rawPercent * 10000) / 10000;
    base = roundedPercent / 100;
  }
  return price * base * (1 + a.eduTaxRatio);
}

export function compare(contract: ContractInfo, finance: FinanceInfo): CompareResponse {
  const { deposit, monthlyRent, type, expiryDate, renewalUsed, housingType } = contract;
  // 주택유형 → HUG 요율 유형. 아파트/연립다세대 둘 다 '주택'이라 세금·대출은 동일.
  const hugType = (housingType ?? '아파트') === '아파트' ? 'apartment' : 'other';
  const { ownCapital, annualIncome, household, firstHome, under35 } = finance;
  const { renewal, oneTime, noticeDeadlineMonths, lendingReg } = RULES;

  const jeonseKb = lendingReg.rates.jeonse_kb;
  const kbBase = lendingReg.rates.kb_mortgage_default;
  const ltvFirst = lendingReg.ltv.first_home.regulated;
  const ltvNohouse = lendingReg.ltv.no_house.regulated;
  const kbCap = lendingReg.mortgage_cap.kb_purchase;
  const govCap = lendingReg.mortgage_cap.gov_metro;
  const dsrCap = lendingReg.dsr.cap;
  const stress = lendingReg.dsr.stress_rate.metro_regulated;
  const baseRatio = lendingReg.dsr.base_ratio;
  const ltr = lendingReg.dsr.loan_type_ratio[lendingReg.dsr.default_loan_type];
  const term = lendingReg.loan_term_years;
  const jeonseCap = lendingReg.jeonse_limit.base;
  const acqReduction = lendingReg.first_home_acq_reduction;

  // ── 날짜 ──
  const expiry = new Date(expiryDate);
  const now = new Date();
  const dday = Math.ceil((expiry.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
  const noticeDeadline = new Date(expiry);
  noticeDeadline.setMonth(noticeDeadline.getMonth() - noticeDeadlineMonths);
  const noticeDaysLeft = Math.ceil((noticeDeadline.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));

  // ── 전세대출 유효 금리 (버팀목 청년 or KB 3.89%) ──
  const bt = buttimok(under35, annualIncome, deposit, ownCapital);
  const jeonseRate = bt.eligible ? bt.rate : jeonseKb;

  // === 갱신 ===
  // 집주인 요구 인상률(확정분) 있으면 min(요구%, 5%)로 — 기존 상한 로직 재사용. null이면 5% 그대로(불변).
  const askPct = contract.renewalAskPct;
  // 확정 갱신 상황을 결정론 resolver로 조합 → 상한(capPct). 상황 없으면 simple_increase 기본(5) = increaseCap → 불변.
  const situations = (contract.renewalSituations ?? []).map(s => String(s));
  const resolution = resolveRenewal(situations, noticeDaysLeft);
  const resCap = resolution.capPct; // % 또는 null(상한 미적용)
  const effectiveCap = (askPct != null)
    ? (resCap == null ? askPct / 100 : Math.min(askPct / 100, resCap / 100))
    : (resCap == null ? 0 : resCap / 100);
  let newDeposit = type === '전세' ? Math.round(deposit * (1 + effectiveCap)) : deposit;
  let newMonthly = type === '월세' ? Math.round(monthlyRent * (1 + effectiveCap)) : 0;
  // 보증금→월세 전환(§7-2, cap과 독립). apply_conversion_cap + 감액분 입력 있을 때만. 전세 방향. 미입력이면 불변.
  let convReduction = 0;
  if (resolution.effects.applyConversionCap && contract.conversionAmount && type === '전세') {
    convReduction = Math.min(contract.conversionAmount, newDeposit);
    const convMonthly = Math.round(convReduction * renewal.conversionRate / 12);
    newDeposit = newDeposit - convReduction;
    newMonthly = newMonthly + convMonthly;
  }
  const depositGap = Math.max(0, newDeposit - deposit);
  const renewalLoanInterest = Math.round(depositGap * jeonseRate / 12);
  const renewalGuarMonthly = Math.round(deposit * guaranteeRate(deposit, hugType) / 12);
  const renewalMonthlyBurden = type === '전세'
    ? renewalLoanInterest + renewalGuarMonthly + newMonthly
    : newMonthly + renewalGuarMonthly;
  const monthlyToDeposit = type === '월세' ? Math.round(monthlyRent * 12 / renewal.conversionRate) : 0;

  // 통보기한 경과 → 동일 조건 묵시적 갱신(인상 0%) 원칙(주임법 §6). compare.py와 오차 0 유지.
  const noticePassed = noticeDaysLeft < 0;
  const renewalHeadline = type === '전세'
    ? (convReduction > 0
        ? `보증금 ${formatAmt(newDeposit)} + 월세 ${Math.round(newMonthly / 10000)}만 (전환)`
        : newDeposit !== deposit ? `보증금 ${formatAmt(deposit)} → ${formatAmt(newDeposit)} (합의 인상 시)` : `보증금 ${formatAmt(deposit)} 그대로`)
    : `월세 ${Math.round(newMonthly / 10000)}만으로 연장`;
  let renewalBasis = noticePassed ? ['통보기한 경과 → 동일 조건 갱신 원칙(주임법 §6)', '법정 상한 5%', 'HUG 공시 요율'] : ['법정 상한 5%', 'HUG 공시 요율'];
  let renewalUncertainty: string | undefined = noticePassed
    ? '통보기한이 지나 임대인이 통보하지 않았다면 동일 조건 묵시적 갱신(인상 0%)이 원칙이에요. 아래 금액은 합의 인상 시 5% 상한 기준입니다.'
    : askPct != null
      ? (askPct <= 5 ? `요구하신 ${askPct}%는 법정 상한(5%) 이내예요.` : `요구 ${askPct}%는 법정 상한을 넘어요 — 상한(5%) 기준으로 계산했어요.`)
      : renewalUsed === '모름'
        ? '갱신권 미사용 시 5% 상한 적용 / 이미 사용 시 협의 필요'
        : renewalUsed === '사용' ? '이미 사용해 법정 갱신은 어려울 수 있어요' : undefined;
  // 확정 상황(requires 통과분)이 있으면 근거·안내를 결정표 원문으로 병치/대체(compare.py와 동일 순서). 상황 없으면 불변.
  if (situations.length && resolution.citations.length) renewalBasis = [...resolution.citations, ...renewalBasis];
  if (situations.length && resolution.guidances.length) renewalUncertainty = resolution.guidances[0];
  const renewalBranch: BranchResult = {
    branch: '갱신',
    headline: renewalHeadline,
    depositOrPrice: newDeposit,
    loanAmount: depositGap,
    oneTimeCost: 0,
    guaranteeMonthly: renewalGuarMonthly,
    monthlyBurden: renewalMonthlyBurden,
    risks: ['보증금 반환 위험 지속', renewalUsed === '사용' ? '법정 갱신권 이미 사용' : '임대인 사정에 따라 거절 가능'],
    cares: [`반환보증 점검 (+${formatAmt(renewalGuarMonthly)}/월)`, '계약서 특약 확인'],
    basis: renewalBasis,
    uncertainty: renewalUncertainty,
    feature: '가장 가볍고 익숙함',
  };

  // === 이사 (전세대출 한도 = 보증금 80%, 최고 2.22억) ===
  const extra = Math.min(Math.round(deposit * 0.80), jeonseCap);
  const moveBudget = deposit + extra;
  const moveInterest = Math.round(extra * jeonseRate / 12);
  const moveGuarMonthly = Math.round(moveBudget * guaranteeRate(moveBudget, hugType) / 12);
  const moveOneTime = Math.round(oneTime.moveBase + brokerFee(deposit));

  const moveBranch: BranchResult = {
    branch: '이사',
    headline: `새 전세 최대 ${formatAmt(moveBudget)}`,
    depositOrPrice: moveBudget,
    loanAmount: extra,
    oneTimeCost: moveOneTime,
    guaranteeMonthly: moveGuarMonthly,
    monthlyBurden: moveInterest + moveGuarMonthly,
    risks: ['새 보증금 잠김', '이사 과정 일회성 비용'],
    cares: ['새 계약 시 전세보증금 반환보증 확인', `일회성 비용 약 ${formatAmt(moveOneTime)}`],
    basis: ['전세대출 한도 80%', '실거래 기준'],
    feature: '환경을 바꿀 기회',
  };

  // === 매매 (수도권 규제지역 가정) ===
  const capital = ownCapital + deposit;
  const ltv = firstHome === '예' ? ltvFirst : ltvNohouse;
  const sizingRate = kbBase + stress * baseRatio * ltr; // 한도 산정용(스트레스)
  const monthlyCapacity = annualIncome * dsrCap / 12; // 기존부채 0
  const dsrLimit = pvAnnuity(monthlyCapacity, sizingRate, term);

  const policy = didimdol(annualIncome, household, firstHome, ownCapital);
  const policyLimit = policy.eligible ? policy.limit : 0;
  const bankCap = Math.min(kbCap, govCap);

  const maxPrice = solveMaxPrice(capital, ltv, dsrLimit, policyLimit, bankCap);
  const needed = maxPrice - capital;
  const policyAmt = policy.eligible ? Math.min(policyLimit, needed) : 0;
  const bankAmt = needed - policyAmt;
  const buyMonthly = Math.round(annuity(policyAmt, policy.rate, term) + annuity(bankAmt, kbBase, term));
  const buyMoveBroker = brokerFee(maxPrice, oneTime.brokerRateBandsPurchase);
  let buyOneTime = Math.round(oneTime.moveBaseBuy + buyMoveBroker + acquisitionFee(maxPrice));
  if (firstHome === '예') buyOneTime = Math.max(0, buyOneTime - acqReduction);

  const buyBasis = [`규제지역 LTV ${Math.round(ltv * 100)}%`, 'KB 한도 3억', '스트레스 DSR 가산 3.0%'];
  if (policy.eligible) buyBasis.push('디딤돌 혼합');

  const buyBranch: BranchResult = {
    branch: '매매',
    headline: `최대 ${formatAmt(maxPrice)} 내 집`,
    depositOrPrice: maxPrice,
    loanAmount: needed,
    oneTimeCost: buyOneTime,
    guaranteeMonthly: 0,
    monthlyBurden: buyMonthly,
    risks: ['자산가치 변동', '원금 장기 상환 부담'],
    cares: ['화재보험 가입', '청약통장 납입 유지'],
    basis: buyBasis,
    feature: '일부는 원금으로 적립',
  };

  const savings = moveOneTime;

  const assumptions = [
    '이 금액은 사전 가늠이며, 실제 대출 심사 결과와 다를 수 있어요',
    '전세대출 금리 HF 공시 평균 3.89%',
    '규제지역 LTV 40% (생애최초 70%)',
    'KB 주택구입 대출 한도 3억 (2026.7~)',
    '스트레스 DSR 수도권 3.0% (한도 산정에만 적용)',
    `보증료 HUG 공시 요율 (${(housingType ?? '아파트') === '아파트' ? '아파트' : '연립·다세대'}·부채비율 80% 이하 가정)`,
    '기존 대출이 없다고 가정했어요. 대출이 있으면 한도가 줄어들 수 있어요',
  ];
  if (firstHome === '모름') assumptions.push('생애최초 주택구입이라면 LTV 70%까지 가능해 한도가 더 늘어날 수 있어요');
  assumptions.push('법정 상한 5%');

  return {
    branches: [renewalBranch, moveBranch, buyBranch],
    dday,
    noticeDaysLeft,
    noticeDeadline: noticeDeadline.toISOString().split('T')[0],
    monthlyToDeposit,
    savings,
    assumptions,
  };
}

function formatAmt(won: number): string {
  if (won >= 100_000_000) {
    const eok = Math.floor(won / 100_000_000);
    const man = Math.round((won % 100_000_000) / 10_000);
    return man > 0 ? `${eok}억 ${man.toLocaleString()}만` : `${eok}억`;
  }
  return `${Math.round(won / 10_000).toLocaleString()}만`;
}
