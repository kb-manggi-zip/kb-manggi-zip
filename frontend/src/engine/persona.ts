// 개인화 조합 레이어 — 로컬(백엔드 미연결) 폴백용 TS 포트.
// 백엔드 app/agents/clarify.py · app/tools/persona.py 의 참조 구현을 옮긴 것.
// (숫자 로직의 정본은 백엔드. 여기는 로컬 데모 백업 — DB 불필요·순수.)
import type { ClarifyResult, PersonaProfile, ContractInfo, FinanceInfo } from '../api/types';

const AXIS_LABEL: Record<string, string> = {
  commute: '통근', consumption: '생활·소비', budget: '예산 여유', preference: '선호지역',
};
const SEGMENT_LABEL: Record<string, string> = {
  '1인': '1인 청년 임차 가구', '신혼': '신혼 가구', '자녀': '자녀 양육 가구',
};

// 국토부 2024 주거실태조사 이사사유 응답률 (backend scoring.py와 동일)
const SURVEY = { commute: 0.561, consumption: 0.24, budget: 0.18, preference: 0.23 };
const PERSONA_ADJUST: Record<string, Record<string, number>> = {
  '1인': { commute: 1.3 },
  '신혼': { budget: 1.3, preference: 1.2 },
  '자녀': { preference: 1.3, consumption: 1.2 },
};

// 자유입력 키워드 → 축별 배수 (창작 금지 — 정해진 축만)
const NOTE_MAP: Array<{ keys: string[]; label: string; boost: Record<string, number> }> = [
  { keys: ['재택', '집에서', '집 주변', '동네에서', '근처에서'], label: '재택·동네생활 중시 → 통근 가중치 절반·생활편의↑', boost: { commute: 0.5, consumption: 1.3 } },
  { keys: ['자차', '차로', '운전', '차 있'], label: '자차 이동 → 통근시간 민감도↓', boost: { commute: 0.7 } },
  { keys: ['도보', '걸어', '걸어서'], label: '도보 생활권 선호 → 선호지역 근접↑', boost: { preference: 1.2 } },
  { keys: ['카페', '외식', '맛집', '배달', '먹'], label: '외식·카페 소비 성향 → 상권 매치↑', boost: { consumption: 1.3 } },
  { keys: ['조용', '한적', '정주', '오래 살'], label: '정주·생활환경 중시 → 선호지역↑', boost: { preference: 1.2 } },
  { keys: ['통근', '출퇴근', '회사', '직장', '가까운 데'], label: '통근 최소화 우선 → 통근↑', boost: { commute: 1.3 } },
  { keys: ['반려동물', '강아지', '고양이', '반려견', '반려묘'], label: '반려동물 — 산책·생활공간 중시 → 선호지역↑·생활편의↑', boost: { preference: 1.2, consumption: 1.2 } },
  { keys: ['학교', '학군', '등하교', '등하원'], label: '자녀 학군 근접 중시 → 선호지역↑', boost: { preference: 1.3 } },
  { keys: ['부모님', '부모님 근처', '가족 근처'], label: '가족 근접 선호 → 선호지역↑', boost: { preference: 1.3 } },
];
const HOUSEHOLD_HINTS: Record<string, string[]> = {
  '자녀': ['아이', '자녀', '학군', '육아', '등원', '등하교', '학교', '어린이집'],
  '신혼': ['결혼', '신혼', '배우자', '부부', '둘이'],
  '1인': ['혼자', '자취', '1인'],
};
const WORKPLACE: Record<string, string> = {
  '1인': '판교(IT)', '신혼': '여의도(금융권)', '자녀': '상암DMC',
};
const CONSUMPTION: Record<string, string[]> = {
  '1인': ['패스트푸드·배달 음식 위주 식사', '취미·여가·구독 지출 활발', '짧은 통근 선호'],
  '신혼': ['주말 나들이·숙박 지출', '유아용품·유아교육 준비 지출 시작', '인터넷쇼핑 비중 큼'],
  '자녀': ['정기 장보기 비중 큼', '교육·학원 지출', '가족 외식 빈도 높음'],
};

function normalize(w: Record<string, number>): Record<string, number> {
  const t = Object.values(w).reduce((a, b) => a + b, 0) || 1;
  return Object.fromEntries(Object.entries(w).map(([k, v]) => [k, Math.round((v / t) * 1000) / 1000]));
}

function noteSignals(note: string) {
  const labels: string[] = [];
  const boost: Record<string, number> = {};
  for (const { keys, label, boost: b } of NOTE_MAP) {
    if (keys.some(k => note.includes(k))) {
      labels.push(label);
      for (const [k, v] of Object.entries(b)) boost[k] = (boost[k] ?? 1) * v;
    }
  }
  return { labels, boost };
}

function noteWeights(household: string, note: string): Record<string, number> {
  const adj = PERSONA_ADJUST[household] ?? {};
  let w = Object.fromEntries(Object.entries(SURVEY).map(([k, v]) => [k, v * (adj[k] ?? 1)]));
  w = normalize(w);
  const { boost } = noteSignals(note);
  w = Object.fromEntries(Object.entries(w).map(([k, v]) => [k, v * (boost[k] ?? 1)]));
  return normalize(w);
}

function axisDir(boost: Record<string, number>, axis: string): number {
  const v = boost[axis] ?? 1;
  return v > 1.05 ? 1 : v < 0.95 ? -1 : 0;
}

export function localClarify(contract: ContractInfo, finance: FinanceInfo, priorNotes: string[] = []): ClarifyResult {
  const household = finance.household ?? '1인';
  const note = contract.note ?? '';
  const sig = noteSignals(note);
  const w = noteWeights(household, note);
  const priorities = Object.entries(w).sort((a, b) => b[1] - a[1]).map(([k]) => AXIS_LABEL[k]);
  const conflicts: string[] = [];
  for (const [seg, keys] of Object.entries(HOUSEHOLD_HINTS)) {
    if (seg !== household && keys.some(k => note.includes(k)))
      conflicts.push(`'${seg}' 관련 언급이 있는데 가구 유형은 '${household}'로 선택하셨어요. 맞는지 확인해 주세요.`);
  }
  // 한 입력 안에 같은 축을 높이는+낮추는 표현이 함께 → 되묻기(조용한 상쇄 금지)
  const dirs: Record<string, Set<number>> = {};
  for (const { keys, boost } of NOTE_MAP) {
    if (keys.some(k => note.includes(k))) {
      for (const [axis, mult] of Object.entries(boost)) {
        const d = mult > 1.05 ? 1 : mult < 0.95 ? -1 : 0;
        if (d) (dirs[axis] ??= new Set()).add(d);
      }
    }
  }
  for (const [axis, ds] of Object.entries(dirs)) {
    if (ds.has(1) && ds.has(-1))
      conflicts.push(`'${AXIS_LABEL[axis]}'을(를) 높이는 표현과 낮추는 표현이 함께 있어요. 어느 쪽으로 반영할지 정해 주세요.`);
  }
  // 이전 반영과 방향 충돌 → 되묻기
  if (priorNotes.length) {
    const prior = noteSignals(priorNotes.join(' ')).boost;
    const nw = noteSignals(note).boost;
    for (const axis of Object.keys(AXIS_LABEL)) {
      const pd = axisDir(prior, axis), nd = axisDir(nw, axis);
      if (pd && nd && pd !== nd)
        conflicts.push(`이전엔 '${AXIS_LABEL[axis]}' 비중을 ${pd < 0 ? '낮추기로' : '높이기로'} 하셨는데 이번엔 반대네요. ${AXIS_LABEL[axis]} 비중을 ${pd < 0 ? '다시 높일까요' : '다시 낮출까요'}?`);
    }
  }
  const questions = [...conflicts];
  if (['통근', '출퇴근', '회사', '직장'].some(k => note.includes(k)))
    questions.push('통근 발품 정확도를 높이려면 주 근무지를 알려주세요 (지금은 가구 유형 기준 대표 직장으로 가정).');
  return { persona: SEGMENT_LABEL[household] ?? '임차 가구', priorities, conflicts, questions, noteSignals: sig.labels };
}

export function localPersona(contract: ContractInfo, finance: FinanceInfo, budget = 0): PersonaProfile {
  const household = finance.household ?? '1인';
  const note = contract.note ?? '';
  const weights = noteWeights(household, note);
  const priorities = Object.entries(weights).sort((a, b) => b[1] - a[1]).map(([k]) => AXIS_LABEL[k]);
  const segment = SEGMENT_LABEL[household] ?? '임차 가구';
  const workplace = WORKPLACE[household];
  const consumption = CONSUMPTION[household] ?? [];
  const resources = [
    ...(workplace ? [`통근 실측 기준 직장: ${workplace} (ODsay)`] : []),
    '반경 상권 집계 (소상공인 상권 API)',
    '국토부 실거래 사례',
    ...(consumption.length ? ['연령 세그먼트 소비 성향 (카드소비 통계)'] : []),
  ];
  const budgetBand = budget > 0
    ? `약 ${(budget / 1e8).toFixed(1)}억 이내 후보에서 선별 (예산 초과 동네는 0단계 하드필터로 제외)`
    : '예산 정보 없음 (월세 등 — 거래 활발 동네 기준)';
  return {
    segment,
    headline: `${segment} · '${priorities[0] ?? '생활 균형'}'을 가장 중시`,
    workplace,
    weights,
    weightBasis: '국토부 2024 주거실태조사 이사사유 응답률 + 가구 세그먼트 조정 (자유입력 시 보정·재정규화)',
    consumption,
    resources,
    budgetBand,
  };
}
