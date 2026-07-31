// 개인화 조합 레이어 — 로컬(백엔드 미연결) 폴백용 TS 포트.
// 백엔드 app/agents/clarify.py · app/tools/persona.py 의 참조 구현을 옮긴 것.
// (숫자 로직의 정본은 백엔드. 여기는 로컬 데모 백업 — DB 불필요·순수.)
import type { ClarifyResult, ConflictItem, PersonaProfile, ContractInfo, FinanceInfo } from '../api/types';

const AXIS_LABEL: Record<string, string> = {
  commute: '통근', consumption: '생활·소비', budget: '예산 여유', preference: '선호지역',
};
const SEGMENT_LABEL: Record<string, string> = {
  '1인': '1인 청년 임차 가구', '신혼': '신혼 가구', '자녀': '자녀 양육 가구',
};

// 국토부 2024 주거실태조사 이사사유 응답률 (backend scoring.py와 동일)
// 2026-07-30: "교통편리·편의문화시설·공원녹지" 25.5%는 commute(순수 통근시간)가 아니라
// consumption(상권·편의시설 밀집도 매칭)에 대응 — commute는 직주근접 30.6%만 남기고,
// consumption 근사(0.24)를 확정값(0.255)으로 대체.
// W1(2026-07-30): 4축 전부 주거실태조사 <표 10> 원문 응답률(commute 30.6 / consumption 25.5 / preference 부모자녀근접8.1+교육3.0=11.1 / budget 집값부담 8.3). backend scoring.py와 동일.
const SURVEY = { commute: 0.306, consumption: 0.255, budget: 0.083, preference: 0.111 };
const PERSONA_ADJUST: Record<string, Record<string, number>> = {
  '1인': { commute: 1.3 },
  '신혼': { budget: 1.3, commute: 1.15 },  // 표10·11 실측: 직주근접↑·편의묶음↓ → preference↑ 폐기, commute↑로 교체
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
  { keys: ['지하철', '전철', '역 가까', '역세권'], label: '대중교통 접근 중시 → 통근 편의↑', boost: { commute: 1.2 } },
  { keys: ['번화가', '시내', '상권 좋', '핫플'], label: '번화가·상권 선호 → 상권 매치↑', boost: { consumption: 1.3 } },
  { keys: ['한적한 동네', '공원', '산책로', '자연'], label: '쾌적·정주 환경 선호 → 선호지역↑', boost: { preference: 1.2 } },
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

// 작업 A·B: 갱신 인상률 '제안' + 상담 사정 보존 (백엔드 clarify.py와 동일 규칙). 숫자는 계산 직행 금지.
function extractRenewalPct(note: string): number | null {
  if (!note) return null;
  if (!['올려', '올리', '올랐', '올렸', '올릴', '인상'].some(k => note.includes(k))) return null;
  const m = note.match(/(\d{1,2})(?:\.\d)?\s*(?:%|퍼센트|프로)/);
  if (!m) return null;
  const v = parseInt(m[1], 10);
  return v > 0 && v <= 100 ? v : null;
}
const CONSULT_KEYS = ['갱신요구권', '갱신권', '실거주', '실입주', '직접 살', '수리', '보수', '누수', '곰팡이', '특약', '보증금 반환', '돌려주', '재계약', '명도', '퇴거', '갱신 거절', '거절당', '소송', '내용증명', '연락이 안', '안 해줘', '안해줘'];
function extractConsultNote(note: string): string {
  if (!note) return '';
  return note.split(/\s*·\s*|[\n。]|(?<=[다요])\s+/).map(s => s.trim()).filter(s => s && CONSULT_KEYS.some(k => s.includes(k))).join(' · ');
}

// 한 입력 안에 같은 축을 높이는+낮추는 표현이 함께 있으면 상충(예: 재택+통근).
function intraNoteConflict(note: string): boolean {
  const dirs: Record<string, Set<number>> = {};
  for (const { keys, boost } of NOTE_MAP) {
    if (keys.some(k => note.includes(k))) {
      for (const [axis, mult] of Object.entries(boost)) {
        const d = mult > 1.05 ? 1 : mult < 0.95 ? -1 : 0;
        if (d) (dirs[axis] ??= new Set()).add(d);
      }
    }
  }
  return Object.values(dirs).some(ds => ds.has(1) && ds.has(-1));
}

// 자유입력이 폼 선택과 다른 가구유형을 시사하면 상충(예: 1인인데 '아이 학군').
function householdConflict(household: string, note: string): boolean {
  return Object.entries(HOUSEHOLD_HINTS).some(([seg, keys]) => seg !== household && keys.some(k => note.includes(k)));
}

function noteWeights(household: string, note: string, adjust?: Record<string, number>): Record<string, number> {
  const adj = PERSONA_ADJUST[household] ?? {};
  let w = Object.fromEntries(Object.entries(SURVEY).map(([k, v]) => [k, v * (adj[k] ?? 1)]));
  w = normalize(w);
  // 확정 adjust 우선. 미확정 입력에 상충(축 내부 상충 or 가구 불일치)이 있으면 반영 보류(B1, 조용한 상쇄 금지).
  const held = !!note && (intraNoteConflict(note) || householdConflict(household, note));
  const boost = adjust && Object.keys(adjust).length ? adjust : (held ? {} : noteSignals(note).boost);
  w = Object.fromEntries(Object.entries(w).map(([k, v]) => [k, v * (boost[k] ?? 1)]));
  return normalize(w);
}

function axisDir(boost: Record<string, number>, axis: string): number {
  const v = boost[axis] ?? 1;
  return v > 1.05 ? 1 : v < 0.95 ? -1 : 0;
}

export function localClarify(contract: ContractInfo, finance: FinanceInfo, priorNotes: string[] = [], householdKnown = true): ClarifyResult {
  const household = finance.household ?? '1인';  // 가중치·세그먼트 기본값(표시용)
  const note = contract.note ?? '';
  const sig = noteSignals(note);
  const w = noteWeights(household, note);
  const priorities = Object.entries(w).sort((a, b) => b[1] - a[1]).map(([k]) => AXIS_LABEL[k]);
  const conflicts: string[] = [];
  // 가구 불일치는 **실제 선택된 값일 때만** — 미선택(householdKnown=false)이면 대조 스킵(J1)
  if (householdKnown && finance.household) {
    for (const [seg, keys] of Object.entries(HOUSEHOLD_HINTS)) {
      if (seg !== household && keys.some(k => note.includes(k)))
        conflicts.push(`'${seg}' 관련 언급이 있는데 가구 유형은 '${household}'로 선택하셨어요. 맞는지 확인해 주세요.`);
    }
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
  const weightAdjust = sig.boost;
  if (['통근', '출퇴근', '회사', '직장'].some(k => note.includes(k)))
    questions.push('통근 발품 정확도를 높이려면 주 근무지를 알려주세요 (지금은 가구 유형 기준 대표 직장으로 가정).');
  return { persona: SEGMENT_LABEL[household] ?? '임차 가구', weightAdjust, held: conflicts.length > 0, priorities, conflicts, questions, noteSignals: sig.labels, renewalAskPct: extractRenewalPct(note), consultNote: extractConsultNote(note) };
}

// SC-14 최종 프로필 종합검증(로컬) — 키워드 '간이 검증'(mode=rule). 백엔드 LLM 없을 때의 폴백.
// conflictItems를 구조로 반환해 인라인 해소(K1)가 로컬 모드에서도 동작하게 한다.
export function localValidateProfile(
  contract: ContractInfo, finance: FinanceInfo, householdKnown = true, acceptedPairs: string[][] = []
): ClarifyResult {
  const household = finance.household ?? '1인';
  const notes = (contract.note ?? '').split(' · ').map(s => s.trim()).filter(Boolean);
  const accepted = new Set(acceptedPairs.map(p => [...p].sort().join('¦')));
  const isAccepted = (a: string, b: string) => accepted.has([a, b].sort().join('¦'));
  const items: ConflictItem[] = [];

  // 가구 불일치(결정론) — 선택 시에만
  if (householdKnown && finance.household) {
    const seen = new Set<string>();
    for (const n of notes)
      for (const [seg, keys] of Object.entries(HOUSEHOLD_HINTS))
        if (seg !== household && !seen.has(seg) && keys.some(k => n.includes(k)) && !isAccepted(household, seg)) {
          seen.add(seg);
          items.push({ type: 'household', optionA: household, optionB: seg, allowBoth: false,
            question: `'${n}' — 가구 유형이 '${SEGMENT_LABEL[household] ?? household}'가 맞나요?` });
        }
  }
  // 축 상충(키워드) — 문장 쌍이 같은 축 반대 방향
  const sigs = notes.map(n => ({ n, boost: noteSignals(n).boost }));
  for (let i = 0; i < sigs.length; i++)
    for (let j = i + 1; j < sigs.length; j++) {
      if (isAccepted(sigs[i].n, sigs[j].n)) continue;
      for (const axis of Object.keys(AXIS_LABEL)) {
        const da = axisDir(sigs[i].boost, axis), db = axisDir(sigs[j].boost, axis);
        if (da && db && da !== db) {
          items.push({ type: 'axis', axis, optionA: sigs[i].n, optionB: sigs[j].n, allowBoth: true,
            question: `'${sigs[i].n}' ↔ '${sigs[j].n}' — '${AXIS_LABEL[axis]}'에서 서로 반대예요.` });
          break;
        }
      }
    }
  for (const n of notes)
    if (intraNoteConflict(n) && !accepted.has([n].join('¦')))
      items.push({ type: 'intra', optionA: n, optionB: '', allowBoth: true, question: `'${n}' 안에 서로 반대되는 내용이 있어요.` });

  const held = items.length > 0;
  const boost = held ? {} : noteSignals(notes.join(' ')).boost;
  const w = noteWeights(household, held ? '' : notes.join(' '));
  return {
    persona: SEGMENT_LABEL[household] ?? '임차 가구',
    weightAdjust: boost,
    held,
    mode: 'rule',
    priorities: Object.entries(w).sort((a, b) => b[1] - a[1]).map(([k]) => AXIS_LABEL[k]),
    conflicts: items.map(c => c.question),
    conflictItems: items,
    questions: items.map(c => c.question),
    noteSignals: noteSignals(notes.join(' ')).labels,
  };
}

export function localPersona(contract: ContractInfo, finance: FinanceInfo, budget = 0): PersonaProfile {
  const household = finance.household ?? '1인';
  const note = contract.note ?? '';
  const baseWeights = noteWeights(household, '');           // 가구 기본(before)
  const weights = noteWeights(household, note, contract.noteAdjust);  // 반영 후(after)
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
    baseWeights,
    weightBasis: '국토부 2024 주거실태조사 이사사유 응답률 + 가구 세그먼트 조정 (자유입력 시 보정·재정규화)',
    consumption,
    resources,
    budgetBand,
  };
}
