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
  note?: string; // 문진 말미 자유입력(선택) — 명확화 노드가 세그먼트·우선순위 축으로 제약 해석
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

export interface JeonseRatio {
  ratio: number;       // 0.87 = 87%
  saleMedian: number;  // 동 매매 중위가(원)
  sampleCount: number; // 매매 표본 수
  band: 'safe' | 'caution' | 'alert';
  label: string;       // 구간 안내 문구
  basis: string;       // "최근 6개월 …동 매매 N건 중위가 기준"
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
  score?: number;        // 개인화 스코어(통계근거 가중합)
  scoreReasons?: string[]; // 왜 이 순위
  jeonseRatio?: JeonseRatio; // 전세 후보일 때 전세가율 리스크 지표(표본<5면 없음)
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

// 명확화(판단 노드) 결과 — 자연어/폼값을 제약된 축으로 해석 + 모순 되묻기(닫힌 루프)
export interface ClarifyResult {
  persona: string;         // 확정 세그먼트 라벨
  priorities: string[];    // 우선순위 축 라벨 순서
  conflicts?: string[];    // 감지된 모순(되묻기)
  questions?: string[];    // 되물을 질문
  noteSignals?: string[];  // 자유입력에서 뽑아낸 제약된 신호
}

// 개인화 '조합' 레이어 산출물 — 완성 페르소나 → 리소스 조합(화면 프로필 카드)
export interface PersonaProfile {
  segment: string;
  headline: string;
  workplace?: string;
  weights: Record<string, number>;
  weightBasis: string;
  consumption: string[];
  resources: string[];
  budgetBand: string;
}

// 지출 집계(합성 마이데이터, 가드레일 T2SQL) — compare에 유입 금지, 리포트 맥락만
export interface SpendAnalysis {
  monthlyTotal: number;
  fixedMonthly: number;
  variableMonthly: number;
  topCategories: { category: string; monthly: number }[];
  trend: { month: string; total: number }[];
  dynamicQueries?: { question: string; sql: string | null; result: number | null; fellBack: boolean; blockReason?: string }[];
  synthetic: boolean;
}

// 만기 결정 리포트 — 최종 산출물(①상황 ②채점 ③동네 ④하루 ⑤지출 ⑥액션)
export interface DecisionReport {
  persona: PersonaProfile;
  clarify?: ClarifyResult;
  comparison: CompareResponse;
  selectedBranch: Branch;
  topRegion?: Region;
  dayBrief: string;
  spend?: SpendAnalysis;
  feasibility: string;
  dday: number;
  noticeDeadline: string;
}

// 분석 에이전트(intake→clarify→compare→route→persona→narrate) 결과
export interface AnalyzeResponse {
  comparison: CompareResponse;
  briefing: string;
  clarify?: ClarifyResult;
  persona?: PersonaProfile;
}
