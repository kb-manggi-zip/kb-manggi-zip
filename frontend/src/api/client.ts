import { compare } from '../engine/compare';
import { REGIONS_BUY, REGIONS_MOVE, REGIONS_MONTHLY } from '../data/regions';
import { SCENES_MOVE, SCENES_BUY, SAVED_MONEY_CARDS } from '../data/scenes';
import { PRODUCTS_RENEWAL, PRODUCTS_MOVE, PRODUCTS_BUY } from '../data/products';
import { PERSONAS } from '../data/personas';
import { briefings } from '../data/briefings';
import { RULES } from '../engine/rules';
import type {
  ContractInfo, FinanceInfo, CompareResponse,
  Region, SimulateResponse, ProductsResponse,
  ReservationRequest, Branch,
  BriefingRequest, BriefingResponse,
  DraftNoticeRequest, DraftNoticeResponse,
} from './types';

// Static exports for screens (screens must not import engine/ or data/ directly)
export { PERSONAS, SAVED_MONEY_CARDS, briefings };
export const NOTICE_DEADLINE_MONTHS = RULES.noticeDeadlineMonths;

const API_URL = import.meta.env.VITE_API_URL;

async function localOrRemote<T>(local: () => T, path: string, opts?: RequestInit): Promise<T> {
  if (!API_URL) return local();
  const res = await fetch(`${API_URL}${path}`, { ...opts, headers: { 'Content-Type': 'application/json' } });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export const api = {
  async compare(req: { contract: ContractInfo; finance: FinanceInfo }): Promise<CompareResponse> {
    return localOrRemote(
      () => compare(req.contract, req.finance),
      '/api/compare',
      { method: 'POST', body: JSON.stringify(req) }
    );
  },

  async regions(branch: Branch, _budget: number): Promise<Region[]> {
    return localOrRemote(
      () => branch === '매매' ? REGIONS_BUY : branch === '이사' ? REGIONS_MOVE : REGIONS_MONTHLY,
      `/api/regions?branch=${branch}&budget=${_budget}`
    );
  },

  async regionsMonthly(): Promise<Region[]> {
    return localOrRemote(() => REGIONS_MONTHLY, '/api/regions?branch=이사-월세');
  },

  async simulate(branch: Branch, _regionId: string): Promise<SimulateResponse> {
    return localOrRemote(
      () => ({
        scenes: branch === '매매' ? SCENES_BUY : SCENES_MOVE,
        monthlyCost: branch === '매매' ? 1_400_000 : 900_000,
      }),
      '/api/simulate',
      { method: 'POST', body: JSON.stringify({ branch, regionId: _regionId }) }
    );
  },

  async products(branch: Branch, _comparison: CompareResponse): Promise<ProductsResponse> {
    return localOrRemote(
      () => branch === '갱신' ? PRODUCTS_RENEWAL : branch === '이사' ? PRODUCTS_MOVE : PRODUCTS_BUY,
      '/api/products',
      { method: 'POST', body: JSON.stringify({ branch }) }
    );
  },

  async reservation(req: ReservationRequest): Promise<void> {
    if (!API_URL) {
      const existing = JSON.parse(localStorage.getItem('kb_reservation') || '[]');
      localStorage.setItem('kb_reservation', JSON.stringify([...existing, req]));
      return;
    }
    await fetch(`${API_URL}/api/reservation`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
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
    if (!API_URL) {
      for (const tok of localText.match(/\S+\s*/g) ?? []) {
        onChunk(tok);
        await new Promise(r => setTimeout(r, 40));
      }
      return;
    }
    const res = await fetch(`${API_URL}/api/briefing/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
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
