// TODO: 모든 수치는 PoC 예시값 — 제출 전 최신 법령/공시 검증 필요
// ⚠️ 백엔드 rules/*.yaml 과 동일 값 유지 (동치). B1.5 리서치 반영분 포함.
export const RULES = {
  renewal: {
    increaseCap: 0.05,       // 법정 상한 5%
    conversionRate: 0.0475,   // 전월세전환율 = 기준금리 2.75%(2026.7.16~) + 법정 2.0%p (렌트홈 4.75%)
  },
  loan: {
    ltv: 0.70,
    dsrCap: 0.40,
    stressRate: 0.045,
    years: 30,
    jeonseRate: 0.038,       // (구) 전세대출 평균 금리 — B1.5에서 lendingReg.rates.jeonse_kb로 대체
  },
  guarantee: {
    feeRate: 0.0015,         // (구) 단일 보증요율 — B1.5에서 guaranteeHug 테이블로 대체
  },
  oneTime: {
    moveBase: 1_500_000,     // 이사 기본 비용
    brokerRate: 0.004,       // 중개 수수료율
    acquisitionRate: 0.011,  // 취득세 등 부대비용율
  },
  noticeDeadlineMonths: 2,   // 갱신 의사 통보 기한

  // ── B1.5 리서치 반영 (backend/rules/lending_regulated.yaml) ──
  lendingReg: {
    ltv: {
      no_house: { non_regulated: 0.70, regulated: 0.40 },
      first_home: { non_regulated: 0.80, regulated: 0.70 },
    },
    mortgage_cap: { gov_metro: 600_000_000, kb_purchase: 300_000_000 },
    dsr: {
      cap: 0.40,
      stress_rate: { metro_regulated: 0.030, local_regulated: 0.015, others: 0.015 },
      base_ratio: 1.0,
      loan_type_ratio: { variable: 1.0, mixed: 1.0, periodic: 1.0 },  // 혼합·주기형 <표2> 미확보 → 보수적 1.0
      default_loan_type: 'variable' as const,
    },
    loan_term_years: 30,
    rates: { kb_mortgage_default: 0.0410, jeonse_kb: 0.0389 },
    jeonse_limit: { base: 222_000_000 },
    first_home_acq_reduction: 2_000_000,
  },

  // backend/rules/policy_loans.yaml
  policyLoans: {
    didimdol: {
      income_cap: { general: 60_000_000, first_home_or_2child: 70_000_000, newlywed: 85_000_000 },
      net_asset_cap: 511_000_000,
      requires_no_house: true,
      limit: { general: 200_000_000, first_home: 240_000_000, newlywed_or_2child: 320_000_000 },
      rate_min: 0.0285,
    },
    buttimok_youth: {
      income_cap: 50_000_000,
      net_asset_cap: 345_000_000,
      ageMin: 19,
      ageMax: 34,
      deposit_cap: 300_000_000,
      limit: 150_000_000,
      rate_by_income: [
        { upto: 20_000_000, rate: 0.022 },
        { upto: 40_000_000, rate: 0.025 },
        { upto: 60_000_000, rate: 0.029 },
        { upto: 75_000_000, rate: 0.033 },
      ],
      local_discount: 0.002,
      rate_floor: 0.010,
    },
  },

  // backend/rules/guarantee_hug.yaml (3중 테이블 — PoC는 apartment·le80 기본)
  guaranteeHug: {
    hug_fee_rate: {
      under_90m:   { apartment: { le80: 0.00115, gt80: 0.00128 } },
      m90_to_200m: { apartment: { le80: 0.00122, gt80: 0.00128 } },
      over_200m:   { apartment: { le80: 0.00122, gt80: 0.00128 } },
    },
    default_house_type: 'apartment' as const,
    default_debt_ratio: 'le80' as const,
  },
};
