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
    id: 'P1',
    label: '전세 사회초년생',
    contract: {
      type: '전세',
      deposit: 200_000_000,
      monthlyRent: 0,
      expiryDate: futureDate(4),
      renewalUsed: '미사용',
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
    },
    finance: {
      annualIncome: 55_000_000,
      ownCapital: 15_000_000,
      household: '1인',
      firstHome: '아니오',
      under35: true,
    },
  },
];
