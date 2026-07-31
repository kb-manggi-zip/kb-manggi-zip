// 백엔드 rules/renewal_cases.yaml + tools/renewal_resolver.py 의 프론트 미러(오차 0 동치용).
// ⚠️ guidance/citation/priority/requires/effect는 yaml과 **글자 단위로 일치**해야 한다
//    (compare.py가 결과 안내/근거로 이 문자열을 쓰고, compare.ts가 동일 값을 내야 하므로).
//    yaml을 고치면 여기도 같이 고칠 것(rules.ts ↔ rules/*.yaml 관계와 동일).

export interface RenewalCase {
  id: string;
  priority: number;
  requires: Record<string, string>;
  effect: { cap_pct?: number | null; warn?: boolean; apply_conversion_cap?: boolean };
  guidance: string;
  citation: string;
}

export const RENEWAL_CASES: RenewalCase[] = [
  {
    id: 'notice_deadline_passed', priority: 100,
    requires: { noticeDaysLeft: '< 0' }, effect: { cap_pct: 0 },
    guidance: '통보기한이 지나 임대인이 통보하지 않았다면 동일 조건 묵시적 갱신(인상 0%)이 원칙이에요.',
    citation: '주택임대차보호법 제6조',
  },
  {
    id: 'renewal_right_exhausted', priority: 90,
    requires: {}, effect: { cap_pct: null, warn: true },
    guidance: '갱신요구권을 이미 사용했다면 5% 상한이 적용되지 않을 수 있어요. 조건은 임대인과의 합의에 따라요.',
    citation: '주택임대차보호법 제6조의3 제1항',
  },
  {
    id: 'jeonse_to_monthly', priority: 80,
    requires: {}, effect: { apply_conversion_cap: true },
    guidance: '전세를 월세로 바꾸자는 요구에는 전월세전환율 상한이 적용돼요.',
    citation: '주택임대차보호법 제7조의2',
  },
  {
    id: 'landlord_self_occupancy', priority: 70,
    requires: {}, effect: {},
    guidance: '임대인 본인이나 직계존비속의 실거주는 갱신 거절 사유에 해당할 수 있어요. 실제 거주하지 않으면 손해배상 청구가 가능해요.',
    citation: '주택임대차보호법 제6조의3 제1항 제8호, 제5항',
  },
  {
    id: 'term_change', priority: 60,
    requires: {}, effect: {},
    guidance: '계약기간 변경은 법정 사항이 아니라 합의 사항이에요. 최소 2년은 임차인이 주장할 수 있어요.',
    citation: '주택임대차보호법 제4조',
  },
  {
    id: 'simple_increase', priority: 10,
    requires: {}, effect: { cap_pct: 5 },
    guidance: '합의로 올리는 경우 법정 상한은 5%예요.',
    citation: '주택임대차보호법 제7조',
  },
];

const _DEFAULT_CAP_PCT = 5;

export interface RenewalResolution {
  capPct: number | null;
  effects: { warn?: boolean; applyConversionCap?: boolean };
  guidances: string[];
  citations: string[];
  applied: string[];
  rejected: { id: string; reason: string }[];
}

function requiresOk(requires: Record<string, string>, facts: Record<string, number>): [boolean, string] {
  for (const [key, cond] of Object.entries(requires || {})) {
    const actual = facts[key];
    if (actual == null) return [false, `${key} 알 수 없음`];
    const parts = String(cond).split(/\s+/);
    if (parts.length !== 2) return [false, `${key} 조건 형식 오류(${cond})`];
    const op = parts[0]; const rhs = parseFloat(parts[1]);
    const table: Record<string, boolean> = {
      '<': actual < rhs, '<=': actual <= rhs, '>': actual > rhs,
      '>=': actual >= rhs, '==': actual === rhs, '!=': actual !== rhs,
    };
    if (!(op in table)) return [false, `${key} 연산자 미지원(${op})`];
    if (!table[op]) return [false, `${key}=${actual} 이 조건 '${cond}' 불충족`];
  }
  return [true, ''];
}

// backend tools/renewal_resolver.py::resolve 의 미러. daysLeft = noticeDaysLeft.
export function resolveRenewal(situations: string[], daysLeft: number): RenewalResolution {
  const byId: Record<string, RenewalCase> = Object.fromEntries(RENEWAL_CASES.map(c => [c.id, c]));
  const facts = { noticeDaysLeft: daysLeft };
  const survivors: RenewalCase[] = [];
  const rejected: { id: string; reason: string }[] = [];
  const seen = new Set<string>();
  for (const sid of situations) {
    if (seen.has(sid)) continue;
    seen.add(sid);
    const c = byId[sid];
    if (!c) { rejected.push({ id: sid, reason: '결정표에 없는 상황(계산 미반영)' }); continue; }
    const [ok, reason] = requiresOk(c.requires, facts);
    if (!ok) { rejected.push({ id: sid, reason }); continue; }
    survivors.push(c);
  }
  survivors.sort((a, b) => b.priority - a.priority);

  let capPct: number | null = _DEFAULT_CAP_PCT;
  for (const c of survivors) {
    if ('cap_pct' in c.effect) { capPct = c.effect.cap_pct ?? null; break; }
  }
  const effects: { warn?: boolean; applyConversionCap?: boolean } = {};
  for (const c of survivors) {
    if (c.effect.warn) effects.warn = true;
    if (c.effect.apply_conversion_cap) effects.applyConversionCap = true;
  }
  return {
    capPct,
    effects,
    guidances: survivors.map(c => c.guidance),
    citations: survivors.map(c => c.citation),
    applied: survivors.map(c => c.id),
    rejected,
  };
}
