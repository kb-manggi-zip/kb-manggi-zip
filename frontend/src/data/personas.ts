import type { ContractInfo, FinanceInfo } from '../api/types';

export interface Persona {
  id: string;
  label: string;
  contract: ContractInfo;
  finance: FinanceInfo;
}

function futureDate(months: number): string {
  const d = new Date();
  d.setMonth(d.getMonth() + months);
  return d.toISOString().split('T')[0];
}

function futureDateDays(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().split('T')[0];
}

export const PERSONAS: Persona[] = [
  {
    // 깨비 — 촬영용 데모 시나리오(김수진 스펙 확정, 2026-08-02): 28세·1인가구·재택근무,
    //   전세 2.8억, 만기 D-90, 집주인 5% 인상 요구. "재택근무예요"를 승인하면
    //   통근 비중↓·상권 비중↑로 동네 순위가 실제로 바뀌는 조합.
    // preferredArea는 원안 성북구 → 마포구로 변경(2026-08-02): 성북구 쪽 후보 동(동선동1가)이
    // 실거래 26건뿐이라 촬영 화면이 빈약함. 소득/자산도 UI 버킷 경계값(4천/3천)이라 실제로 선택
    // 불가능한 숫자였어서 대표값(4~5천=4,500만/3~5천=4,000만)으로 조정. 나머지 스펙은 원안 그대로.
    // 마포구·이사 갈래 기준 실제 추천 2위 = 노고산동(태그 3개 다 있음+전세 실거래 78건) — 데모 지역으로 사용.
    id: 'P1',
    label: '깨비 · 전세 사회초년생 · 마포',
    contract: {
      type: '전세',
      deposit: 280_000_000,
      monthlyRent: 0,
      expiryDate: futureDateDays(90),
      renewalUsed: '미사용',
      housingType: '아파트',
      preferredArea: '마포구',
      renewalAskPct: 5,
      note: '재택근무예요',
    },
    finance: {
      annualIncome: 45_000_000,
      ownCapital: 40_000_000,
      household: '1인',
      firstHome: '모름',
      under35: true,
    },
  },
  {
    id: 'P2',
    label: '신혼 전세 3.2억',
    contract: {
      type: '전세',
      deposit: 320_000_000,
      monthlyRent: 0,
      expiryDate: futureDate(3),
      renewalUsed: '미사용',
      housingType: '아파트',
    },
    finance: {
      annualIncome: 80_000_000,
      ownCapital: 60_000_000,
      household: '신혼',
      firstHome: '예',
      under35: true,
    },
  },
  {
    id: 'P3',
    label: '월세 2천/80',
    contract: {
      type: '월세',
      deposit: 80_000_000,
      monthlyRent: 2_000_000,
      expiryDate: futureDate(5),
      renewalUsed: '모름',
      housingType: '연립다세대',
    },
    finance: {
      annualIncome: 55_000_000,
      ownCapital: 15_000_000,
      household: '1인',
      firstHome: '아니오',
      under35: true,
    },
  },
  {
    // S2(기준·묵시적 갱신): 자녀 가구 + 통보기한 경과 상태.
    //   expiryDate=1개월 후 → 통보기한(만기 2개월 전)이 이미 지나 '묵시적 갱신(동일 조건)' 안내가 뜬다.
    //   household='자녀'라 "아이 학교가 중요해요" 입력 시 모순 감지 없이 선호지역 상향으로 반영된다.
    //   (지출 분석 ⑤는 합성 마이데이터에 자녀 페르소나가 없어 P1로 매핑됨 — 데모 한계, 갱신 시연엔 무관)
    id: 'P4',
    label: '자녀 가구 · 통보기한 경과',
    contract: {
      type: '전세',
      deposit: 400_000_000,
      monthlyRent: 0,
      expiryDate: futureDate(1),
      renewalUsed: '미사용',
      housingType: '아파트',
    },
    finance: {
      annualIncome: 70_000_000,
      ownCapital: 50_000_000,
      household: '자녀',
      firstHome: '모름',
      under35: false,
    },
  },
];
