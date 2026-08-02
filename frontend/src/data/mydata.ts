// 로컬(오프라인) 모드용 합성 마이데이터 집계 — 백엔드 spend_query.standard_aggregates 출력과 동일값.
// 값 출처: 백엔드 실행 결과(P1/P2/P3). 원격 모드에선 이 파일을 쓰지 않고 백엔드 집계를 그대로 받는다.
// 실서비스는 마이데이터 동의 후 실내역으로 교체(현재는 합성 3인 — 화면에 명시).
export interface MydataAgg {
  monthlyTotal: number;
  fixedMonthly: number;
  variableMonthly: number; // = 여력
  topCategories: { category: string; monthly: number }[];
}

export const MYDATA: Record<string, MydataAgg> = {
  P1: {
    monthlyTotal: 1_959_985,
    fixedMonthly: 890_000,
    variableMonthly: 1_069_985,
    topCategories: [
      { category: '주거', monthly: 700_000 },
      { category: '식비', monthly: 249_997 },
      { category: '쇼핑', monthly: 249_997 },
    ],
  },
  P2: {
    monthlyTotal: 2_739_982,
    fixedMonthly: 1_210_000,
    variableMonthly: 1_529_982,
    topCategories: [
      { category: '주거', monthly: 950_000 },
      { category: '쇼핑', monthly: 499_998 },
      { category: '식비', monthly: 499_996 },
    ],
  },
  P3: {
    monthlyTotal: 2_079_988,
    fixedMonthly: 1_010_000,
    variableMonthly: 1_069_988,
    topCategories: [
      { category: '주거', monthly: 750_000 },
      { category: '여가', monthly: 349_997 },
      { category: '식비', monthly: 299_997 },
    ],
  },
};
