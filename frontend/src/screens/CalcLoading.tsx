import React, { useEffect, useState } from 'react';
import { useApp } from '../store';
import { COLORS, BRANCH_ICONS } from '../theme';
import { MobileShell } from '../components/ui';
import { api } from '../api/client';

const BRANCHES = ['갱신', '이사', '매매'] as const;

export default function CalcLoading() {
  const { state, dispatch } = useApp();
  const [activeIdx, setActiveIdx] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const interval = setInterval(() => {
      setActiveIdx(i => (i + 1) % 3);
    }, 250);

    const calc = async () => {
      if (!state.contract || !state.finance) {
        dispatch({ type: 'NAVIGATE', screen: 'SC-02' });
        return;
      }
      try {
        await new Promise(r => setTimeout(r, 800));
        // 분석 에이전트 실행 (원격이면 intake→compare→narrate 그래프가 Langfuse에 찍힘)
        const result = await api.analyze({ contract: state.contract, finance: state.finance });
        dispatch({ type: 'SET_COMPARISON', comparison: result.comparison });
        dispatch({ type: 'NAVIGATE', screen: 'SC-03' });
      } catch (e) {
        setError('계산 중 오류가 발생했어요. 다시 시도해주세요.');
      }
    };

    calc();
    return () => clearInterval(interval);
  }, []);

  return (
    <MobileShell className="items-center justify-center">
      <div className="flex flex-col items-center gap-8 px-8">
        <div
          className="w-16 h-16 rounded-2xl flex items-center justify-center font-black text-foreground text-xl"
          style={{ background: COLORS.KB_YELLOW }}
        >
          KB
        </div>

        <div className="text-center space-y-2">
          <p className="text-lg font-bold text-foreground">눌러앉기·옮기기·사기, 세 경우를 계산하고 있어요</p>
          <p className="text-sm text-muted-foreground">잠시만 기다려주세요</p>
        </div>

        <div className="flex gap-6">
          {BRANCHES.map((b, i) => (
            <div
              key={b}
              className="flex flex-col items-center gap-1 transition-all duration-300"
              style={{ opacity: activeIdx === i ? 1 : 0.3, transform: activeIdx === i ? 'scale(1.2)' : 'scale(1)' }}
            >
              <span className="text-3xl">{BRANCH_ICONS[b]}</span>
              <span className="text-xs text-muted-foreground">{b}</span>
            </div>
          ))}
        </div>

        {/* 스피너 */}
        <div
          className="w-8 h-8 rounded-full border-2 border-muted animate-spin"
          style={{ borderTopColor: COLORS.KB_YELLOW }}
        />

        {error && (
          <div className="text-center space-y-3">
            <p className="text-sm text-destructive">{error}</p>
            <button
              onClick={() => { setError(null); window.location.reload(); }}
              className="text-sm font-medium underline"
              style={{ color: COLORS.KB_YELLOW }}
            >
              다시 시도
            </button>
          </div>
        )}
      </div>

      <p className="absolute bottom-8 px-8 text-xs text-center text-muted-foreground">
        상담 예약은 영업 연락이 아니라,<br />요청하신 상담 연결을 위한 거예요.
      </p>
    </MobileShell>
  );
}
