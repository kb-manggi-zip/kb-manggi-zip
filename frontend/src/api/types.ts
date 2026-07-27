// 백엔드 Pydantic 모델과 1:1 계약 — 임의 변경 금지
export type ContractType = '전세' | '월세';
export type RenewalUsed = '미사용' | '사용' | '모름';
export type HousingType = '아파트' | '연립다세대'; // 국토부 API property_type과 동일 값. 화면엔 "원룸·투룸·빌라"로 표시. 둘 다 법적 '주택'
export type Household = '1인' | '신혼' | '자녀';
export type FirstHome = '예' | '아니오' | '모름';
export type Branch = '갱신' | '이사' | '매매';

export interface ContractInfo {
  type: ContractType;
  deposit: number;
  monthlyRent: number;
  expiryDate: string; // ISO date string
  renewalUsed: RenewalUsed;
  housingType?: HousingType; // HUG 보증료 요율만 좌우(세금·대출은 둘 다 주택 동일). 기본 아파트
  preferredArea?: string; // 선호지역 구명(예 '마포구') — 동네 후보를 그 구에서 우선. 빈값=전체
}

export interface FinanceInfo {
  annualIncome: number;
  ownCapital: number;
  household: Household;
  firstHome: FirstHome;   // 생애최초 주택구입 여부 (B1.5)
  under35: boolean;       // 만 35세 미만 (버팀목 청년 자격) (B1.5)
}

export interface BranchResult {
  branch: Branch;
  headline: string;
  depositOrPrice: number;
  loanAmount: number;
  oneTimeCost: number;
  guaranteeMonthly: number;
  monthlyBurden: number;
  risks: string[];
  cares: string[];
  basis: string[];
  uncertainty?: string;
  feature: string;
}

export interface CompareResponse {
  branches: BranchResult[];
  dday: number;
  noticeDaysLeft: number;
  noticeDeadline: string;
  monthlyToDeposit: number; // 월세→보증금 환산 (월세만)
  savings: number; // 갱신 시 아끼는 일회성 비용
  assumptions: string[];
}

export interface Region {
  id: string;
  name: string;
  midPrice: number; // 중위 매매/전세가
  monthlyMidPrice?: number;
  surplus: number; // 예산 여유 (계산값)
  tradeCount: number;
  tags: string[];
  lat: number;
  lng: number;
  branch: Branch;
}

export interface Scene {
  time: string;
  emoji: string;
  visual: string; // unsplash URL
  caption1: string;
  caption2: string;
  basis?: string;
}

export interface SimulateResponse {
  scenes: Scene[];
  monthlyCost: number;
}

export interface Product {
  name: string;
  condition: string;
  recommendReason: string;
  monthlyPayment?: number;
  maxAmount?: number;
  basis: string;
}

export interface ProductsResponse {
  branch: Branch;
  mainLoan: Product;
  guarantee?: Product;
  extra?: Product;
}

export interface ReservationRequest {
  branch: Branch;
  date: string;
  productName: string;
}

// 기존 인터페이스 수정 금지 — 추가만
export interface BriefingRequest {
  kind: 'compare' | 'regions' | 'renewal' | 'revisit' | 'dayPlayer' | 'savedMoney' | 'finance';
  context: Record<string, unknown>;
}

export interface BriefingResponse {
  text: string;
}

export interface DraftNoticeRequest {
  expiryDate: string;
  address?: string;
}

export interface DraftNoticeResponse {
  draft: string;
}

// 분석 에이전트(intake→compare→narrate) 결과 — 계산 + 개인화 통역
export interface AnalyzeResponse {
  comparison: CompareResponse;
  briefing: string;
}
