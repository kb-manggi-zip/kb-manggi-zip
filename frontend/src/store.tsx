import React, { createContext, useContext, useReducer, useEffect } from 'react';
import type { ContractInfo, FinanceInfo, CompareResponse, Branch } from './api/types';

export type Screen =
  | 'SC-01' | 'SC-02' | 'SC-03' | 'SC-04' | 'SC-05'
  | 'SC-06' | 'SC-07' | 'SC-08' | 'SC-09' | 'SC-10'
  | 'SC-11' | 'SC-12';

export interface AppState {
  screen: Screen;
  contract: ContractInfo | null;
  finance: FinanceInfo | null;
  comparison: CompareResponse | null;
  briefing: string | null;   // 분석 에이전트(narrate 노드)가 생성한 개인화 통역
  selectedBranch: Branch | null;
  selectedRegionId: string | null;
  reminderOn: boolean;
  reservationDate: string | null;
}

type Action =
  | { type: 'NAVIGATE'; screen: Screen }
  | { type: 'SET_CONTRACT'; contract: ContractInfo }
  | { type: 'SET_FINANCE'; finance: FinanceInfo }
  | { type: 'SET_COMPARISON'; comparison: CompareResponse; briefing?: string }
  | { type: 'SELECT_BRANCH'; branch: Branch }
  | { type: 'SELECT_REGION'; regionId: string }
  | { type: 'TOGGLE_REMINDER' }
  | { type: 'SET_RESERVATION'; date: string }
  | { type: 'RESET' }
  | { type: 'RESTORE'; state: Partial<AppState> };

const INITIAL: AppState = {
  screen: 'SC-01',
  contract: null,
  finance: null,
  comparison: null,
  briefing: null,
  selectedBranch: null,
  selectedRegionId: null,
  reminderOn: true,
  reservationDate: null,
};

function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case 'NAVIGATE': return { ...state, screen: action.screen };
    case 'SET_CONTRACT': return { ...state, contract: action.contract };
    case 'SET_FINANCE': return { ...state, finance: action.finance };
    case 'SET_COMPARISON': return { ...state, comparison: action.comparison, briefing: action.briefing ?? null };
    case 'SELECT_BRANCH': return { ...state, selectedBranch: action.branch };
    case 'SELECT_REGION': return { ...state, selectedRegionId: action.regionId };
    case 'TOGGLE_REMINDER': return { ...state, reminderOn: !state.reminderOn };
    case 'SET_RESERVATION': return { ...state, reservationDate: action.date };
    case 'RESET': return { ...INITIAL };   // 이전 설문/계산 전부 초기화 (persist가 localStorage도 비움)
    case 'RESTORE': return { ...state, ...action.state };
    default: return state;
  }
}

const Ctx = createContext<{ state: AppState; dispatch: React.Dispatch<Action> } | null>(null);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(reducer, INITIAL);

  useEffect(() => {
    const saved = localStorage.getItem('kb_app_state');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        dispatch({ type: 'RESTORE', state: { ...parsed, screen: 'SC-01' } });
      } catch {}
    }
  }, []);

  useEffect(() => {
    const { screen: _screen, ...persisted } = state;
    localStorage.setItem('kb_app_state', JSON.stringify(persisted));
  }, [state]);

  return <Ctx.Provider value={{ state, dispatch }}>{children}</Ctx.Provider>;
}

export function useApp() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useApp must be used within AppProvider');
  return ctx;
}
