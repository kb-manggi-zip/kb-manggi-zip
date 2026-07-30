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

export const PERSONAS: Persona[] = [
  {
    // S1(재택 1인): 성북구·이사 예산 5억대에서 재택 확정이 동네 순위를 실제로 뒤집는 조합(검증됨).
    //   재택 확정 시 top1: 동선동1가 → 동선동4가 (통근 비중↓·상권 비중↑). preferredArea가 성북 필터.
    id: 'P1',
    label: '전세 사회초년생 · 성북',
    contract: {
      type: '전세',
      deposit: 280_000_000,
      monthlyRent: 0,
      expiryDate: futureDate(4),
      renewalUsed: '미사용',
      housingType: '아파트',
      preferredArea: '성북구',
    },
    finance: {
      annualIncome: 40_000_000,
      ownCapital: 30_000_000,
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
