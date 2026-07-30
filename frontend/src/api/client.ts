import { compare } from '../engine/compare';
import { localClarify, localPersona, localValidateProfile } from '../engine/persona';
import { REGIONS_BUY, REGIONS_MOVE, REGIONS_MONTHLY } from '../data/regions';
import { SCENES_MOVE, SCENES_BUY, SCENES_STAY, SCENES_BY_REGION, SAVED_MONEY_CARDS } from '../data/scenes';
import { PRODUCTS_RENEWAL, PRODUCTS_MOVE, PRODUCTS_MOVE_MONTHLY, PRODUCTS_BUY } from '../data/products';
import { PERSONAS } from '../data/personas';
import { briefings } from '../data/briefings';
import { RULES } from '../engine/rules';
import { getSessionId } from './session';
import { formatAmount } from '../utils/format';
import type {
  ContractInfo, FinanceInfo, CompareResponse,
  Region, SimulateResponse, ProductsResponse,
  ReservationRequest, Branch, HousingType,
  BriefingRequest, BriefingResponse,
  DraftNoticeRequest, DraftNoticeResponse,
  AnalyzeResponse, ClarifyResult, PersonaProfile, DecisionReport,
} from './types';

// Static exports for screens (screens must not import engine/ or data/ directly)
export { PERSONAS, SAVED_MONEY_CARDS, briefings };
export const NOTICE_DEADLINE_MONTHS = RULES.noticeDeadlineMonths;

// 원격(백엔드) 연결 모드 판별:
//  - VITE_API_URL 설정 → 그 절대주소로 호출(별도 백엔드, 예: Render).
//  - VITE_REMOTE=1 (주소 없음) → same-origin 상대경로 '/api/...'(프론트·백엔드 한 배포, 예: 단일 Vercel).
//  - 둘 다 없음 → 로컬 폴백(engine/·data/). 데모 백업.
const API_URL = import.meta.env.VITE_API_URL ?? '';
const IS_REMOTE = import.meta.env.VITE_REMOTE === '1' || !!API_URL;

// 원격 호출 공통 헤더 — Content-Type + 여정 세션ID(Langfuse Sessions 그룹핑).
function apiHeaders(): Record<string, string> {
  return { 'Content-Type': 'application/json', 'X-Session-Id': getSessionId() };
}

async function localOrRemote<T>(local: () => T, path: string, opts?: RequestInit): Promise<T> {
  if (!IS_REMOTE) return local();
  const res = await fetch(`${API_URL}${path}`, { ...opts, headers: apiHeaders() });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

// 데모 매핑: 가구/계약 → 합성 마이데이터 페르소나(P1/P2/P3). 백엔드 report.persona_id_for와 동일.
export function personaIdFor(contract: ContractInfo | null, finance: FinanceInfo | null): string {
  if (finance?.household === '신혼') return 'P2';
  if (contract?.type === '월세') return 'P3';
  return 'P1';
}

export const api = {
  async compare(req: { contract: ContractInfo; finance: FinanceInfo }): Promise<CompareResponse> {
    return localOrRemote(
      () => compare(req.contract, req.finance),
      '/api/compare',
      { method: 'POST', body: JSON.stringify(req) }
    );
  },

  // 분석 에이전트 — 원격이면 intake→compare→narrate 그래프(Langfuse 추적), 로컬이면 engine 계산.
  async analyze(req: { contract: ContractInfo; finance: FinanceInfo }): Promise<AnalyzeResponse> {
    return localOrRemote(
      () => ({ comparison: compare(req.contract, req.finance), briefing: '' }),
      '/api/analyze',
      { method: 'POST', body: JSON.stringify(req) }
    );
  },

  // 명확화(판단) — 자연어/폼값 → 제약 해석 + 모순 되묻기(가구불일치·이전 반영 충돌). priorNotes=확정된 조정들.
  async clarify(contract: ContractInfo, finance: FinanceInfo, priorNotes: string[] = [], householdKnown = true): Promise<ClarifyResult> {
    return localOrRemote(
      () => localClarify(contract, finance, priorNotes, householdKnown),
      '/api/clarify',
      // householdSelected=false면 가구 유형 미선택 → 상충 감지에서 제외(J1). 기본 true(하위호환).
      { method: 'POST', body: JSON.stringify({ contract, finance, priorNotes, householdSelected: householdKnown }) }
    );
  },

  // SC-14 최종 프로필 종합검증 — 누적 자유입력+가구+예산을 한 번에 의미 검증(원격 LLM) / 간이 검증(로컬 키워드).
  // acceptedPairs: '둘 다 맞아요'로 확인한 신호 쌍 — 재검증 시 상충에서 제외(K1).
  async validateProfile(contract: ContractInfo, finance: FinanceInfo, budget = 0, householdKnown = true, acceptedPairs: string[][] = []): Promise<ClarifyResult> {
    return localOrRemote(
      () => localValidateProfile(contract, finance, householdKnown, acceptedPairs),
      '/api/validate-profile',
      { method: 'POST', body: JSON.stringify({ contract, finance, budget, householdSelected: householdKnown, acceptedPairs }) }
    );
  },

  // HITL 확정 이벤트 — 관측 전용(Langfuse 세션에 '제안→사용자 확정' 기록). 로컬 모드는 no-op.
  async hitl(choice: 'applied' | 'skipped', signals: string[], note: string): Promise<void> {
    if (!IS_REMOTE) return;
    try {
      await fetch(`${API_URL}/api/hitl`, {
        method: 'POST', headers: apiHeaders(),
        body: JSON.stringify({ choice, signals, note }),
      });
    } catch { /* 관측 실패는 UX를 막지 않음 */ }
  },

  // 개인화 조합 레이어 — 완성 페르소나 → 리소스 조합 산출물(프로필 카드). budget=밴드 표기, personaId=실측 소비 override.
  async persona(contract: ContractInfo, finance: FinanceInfo, budget = 0): Promise<PersonaProfile> {
    const pid = personaIdFor(contract, finance);
    return localOrRemote(
      () => localPersona(contract, finance, budget),
      `/api/persona?budget=${budget}&personaId=${pid}`,
      { method: 'POST', body: JSON.stringify({ contract, finance }) }
    );
  },

  // 만기 결정 리포트 — 원격이면 백엔드 조립(⑤ 지출=합성 마이데이터 T2SQL), 로컬이면 compare+persona만(⑤ 생략).
  async report(contract: ContractInfo, finance: FinanceInfo, branch: Branch, personaId?: string, regionId?: string): Promise<DecisionReport> {
    return localOrRemote(
      () => {
        const cmp = compare(contract, finance);
        // 갱신: 새 발품 대신 '현재 동네 유지' 연속성 요약(백엔드 report.py와 동일 취지, B7)
        const moveCost = cmp.branches.find(b => b.branch === '이사')?.oneTimeCost ?? 0;
        const stayBrief = `${contract.preferredArea || '지금 사는 동네'}에서의 익숙한 동선을 그대로 이어가요. 새로 적응할 동네도, 발품도 필요 없어요. 이사였다면 들었을 일회성 비용 약 ${formatAmount(moveCost)}을(를) 아끼는 셈이에요.`;
        return {
          persona: localPersona(contract, finance),
          clarify: localClarify(contract, finance),
          comparison: cmp,
          selectedBranch: branch,
          dayBrief: branch === '갱신' ? stayBrief : '',
          feasibility: '지출로 본 실현 가능성은 백엔드 연결(합성 마이데이터) 시 제공됩니다.',
          dday: cmp.dday,
          noticeDeadline: cmp.noticeDeadline,
        };
      },
      '/api/report',
      // regionId = 사용자가 실제로 본 '선택한 동네'(L5) → 리포트가 그 동네 기준으로 나오게
      { method: 'POST', body: JSON.stringify({ contract, finance, branch, personaId, regionId }) }
    );
  },

  async regions(branch: Branch, _budget: number, housingType?: HousingType, preferredArea?: string, household?: string, note?: string, personaId?: string, noteAdjust?: Record<string, number>): Promise<Region[]> {
    const hasAdjust = noteAdjust && Object.keys(noteAdjust).length > 0;
    const q = (housingType ? `&housingType=${housingType}` : '')
      + (preferredArea ? `&preferredArea=${encodeURIComponent(preferredArea)}` : '')
      + (household ? `&household=${encodeURIComponent(household)}` : '')
      + (note ? `&note=${encodeURIComponent(note)}` : '')
      + (hasAdjust ? `&adjust=${encodeURIComponent(JSON.stringify(noteAdjust))}` : '')
      + (personaId ? `&personaId=${personaId}` : '');
    return localOrRemote(
      () => branch === '매매' ? REGIONS_BUY : branch === '이사' ? REGIONS_MOVE : REGIONS_MONTHLY,
      `/api/regions?branch=${branch}&budget=${_budget}${q}`
    );
  },

  async regionsMonthly(housingType?: HousingType, preferredArea?: string, household?: string): Promise<Region[]> {
    const q = (housingType ? `&housingType=${housingType}` : '')
      + (preferredArea ? `&preferredArea=${encodeURIComponent(preferredArea)}` : '')
      + (household ? `&household=${encodeURIComponent(household)}` : '');
    return localOrRemote(() => REGIONS_MONTHLY, `/api/regions?branch=이사-월세${q}`);
  },

  async simulate(branch: Branch, _regionId: string): Promise<SimulateResponse> {
    return localOrRemote(
      () => ({
        // 지역별 씬(regionId) 우선 → 없으면 branch 기본. '월세로'('-m')와 '전세로'가 다른 하루.
        scenes:
          SCENES_BY_REGION[_regionId] ??
          (branch === '매매' ? SCENES_BUY : branch === '갱신' ? SCENES_STAY : SCENES_MOVE),
        monthlyCost: branch === '매매' ? 1_400_000 : 900_000,
      }),
      '/api/simulate',
      { method: 'POST', body: JSON.stringify({ branch, regionId: _regionId }) }
    );
  },

  // '이 동네에서의 하루' 개인화 발품 내레이션 (agent 모드: 백엔드 LLM+소비프로필 / 로컬: 템플릿)
  async dayLifestyle(region: Region | null, branch: Branch, finance: FinanceInfo | null, budget?: number, wfh?: boolean): Promise<string> {
    const regionName = region?.name ?? '이 동네';
    const local = () => briefings.dayPlayer(regionName);
    if (!IS_REMOTE) return local();
    try {
      const res = await fetch(`${API_URL}/api/briefing`, {
        method: 'POST',
        headers: apiHeaders(),
        // budget = 고른 갈래 예산(발품 실거래를 예산 이하에서 뽑는 캡, G2) / wfh = 재택 확정 시 통근 격하(G3)
        body: JSON.stringify({ kind: 'dayPlayer', context: { region, regionName, branch, finance, budget, wfh } }),
      });
      if (!res.ok) return local();
      const j = await res.json();
      return (j?.text as string) || local();   // 실패·빈 응답이면 로컬 템플릿으로 안전 폴백
    } catch {
      return local();
    }
  },

  async products(branch: Branch, _comparison: CompareResponse, contract?: ContractInfo): Promise<ProductsResponse> {
    return localOrRemote(
      () => branch === '갱신' ? PRODUCTS_RENEWAL
        : branch === '이사' ? (contract?.type === '월세' ? PRODUCTS_MOVE_MONTHLY : PRODUCTS_MOVE)
        : PRODUCTS_BUY,
      '/api/products',
      { method: 'POST', body: JSON.stringify({ branch, contract }) }
    );
  },

  async reservation(req: ReservationRequest): Promise<void> {
    if (!IS_REMOTE) {
      const existing = JSON.parse(localStorage.getItem('kb_reservation') || '[]');
      localStorage.setItem('kb_reservation', JSON.stringify([...existing, req]));
      return;
    }
    await fetch(`${API_URL}/api/reservation`, {
      method: 'POST',
      headers: apiHeaders(),
      body: JSON.stringify(req),
    });
  },

  async briefing(_req: BriefingRequest): Promise<BriefingResponse> {
    // 로컬: briefings 템플릿 사용 / 원격: POST /api/briefing
    // 실제 텍스트 생성은 호출 측에서 briefings.* 직접 사용
    return localOrRemote(
      () => ({ text: '' }),
      '/api/briefing',
      { method: 'POST', body: JSON.stringify(_req) }
    );
  },

  // SSE 스트리밍: 원격이면 서버 토큰을, 로컬이면 폴백 텍스트를 어절 단위로 onChunk에 흘림.
  // (양쪽 동일 타이핑 UX — AiBriefing은 live 모드로 점진 렌더)
  async streamBriefing(
    req: BriefingRequest,
    onChunk: (text: string) => void,
    localText: string,
  ): Promise<void> {
    if (!IS_REMOTE) {
      for (const tok of localText.match(/\S+\s*/g) ?? []) {
        onChunk(tok);
        await new Promise(r => setTimeout(r, 40));
      }
      return;
    }
    const res = await fetch(`${API_URL}/api/briefing/stream`, {
      method: 'POST',
      headers: apiHeaders(),
      body: JSON.stringify(req),
    });
    if (!res.ok || !res.body) throw new Error(`SSE error: ${res.status}`);
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split(/\r?\n\r?\n/);
      buffer = events.pop() ?? '';
      for (const ev of events) {
        if (/(^|\n)event:\s*done/.test(ev)) continue;       // 종료 이벤트 무시
        const data = ev
          .split(/\r?\n/)
          .filter(l => l.startsWith('data:'))
          .map(l => l.slice(5).replace(/^ /, ''))            // "data: " 뒤 한 칸만 제거
          .join('');
        if (data && data !== '[DONE]') onChunk(data);
      }
    }
  },

  async draftNotice(req: DraftNoticeRequest): Promise<DraftNoticeResponse> {
    return localOrRemote(
      () => {
        const expiry = req.expiryDate
          ? new Date(req.expiryDate).toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' })
          : '[만기일]';
        const addr = req.address || '[동·호수]';
        return {
          draft:
            `안녕하세요, ${addr}에 거주 중인 임차인입니다.\n\n` +
            `${expiry}자로 계약이 만료되어, 주택임대차보호법에 따른 계약갱신을 요청드리고자 연락드립니다.\n\n` +
            `조건 협의가 필요하시면 편하신 시간에 말씀 부탁드립니다.\n\n` +
            `감사합니다.`,
        };
      },
      '/api/draft-notice',
      { method: 'POST', body: JSON.stringify(req) }
    );
  },
};
