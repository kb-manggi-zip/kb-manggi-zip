import React, { useEffect, useState } from 'react';
import { useApp } from '../store';
import { COLORS } from '../theme';
import { MobileShell, FlowProgress, BackBtn, Disclaimer } from '../components/ui';
import AiBriefing from '../components/AiBriefing';
import { api, briefings } from '../api/client';
import { formatAmount } from '../utils/format';
import type { Region } from '../api/types';

type Tab = 'similar' | 'upgrade';

export default function RegionListMonthly() {
  const { state, dispatch } = useApp();
  const [tab, setTab] = useState<Tab>('similar');
  const [regions, setRegions] = useState<Region[]>([]);

  useEffect(() => {
    api.regionsMonthly(state.contract?.housingType).then(setRegions);
  }, [state.contract?.housingType]);

  function selectRegion(r: Region) {
    dispatch({ type: 'SELECT_REGION', regionId: r.id, region: r });
    dispatch({ type: 'NAVIGATE', screen: 'SC-07' });
  }

  return (
    <MobileShell>
      <FlowProgress current={3} />

      <div className="flex items-center gap-2 px-5 py-3 border-b-2" style={{ borderColor: COLORS.BLUE }}>
        <BackBtn onClick={() => dispatch({ type: 'NAVIGATE', screen: 'SC-03' })} />
        <span className="text-lg">🚚</span>
        <span className="font-bold" style={{ color: COLORS.BLUE }}>이사 · 월세 동네 후보</span>
      </div>

      {/* 서브 탭 */}
      <div className="flex gap-0 mx-5 mt-4 rounded-2xl overflow-hidden border border-border">
        {([['similar', '비슷한 월세로'], ['upgrade', '전세로 갈아타기']] as [Tab, string][]).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className="flex-1 py-3 text-sm font-semibold transition-colors"
            style={{
              background: tab === key ? COLORS.BLUE : COLORS.CARD,
              color: tab === key ? '#fff' : COLORS.SUB,
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === 'upgrade' && (
        <div className="mx-5 mt-3 px-4 py-2.5 bg-muted rounded-xl text-xs text-muted-foreground">
          🛡 전세 전환 시 반환보증 가입을 함께 확인하세요.
        </div>
      )}

      {/* AI 브리핑 */}
      {regions.length > 0 && (
        <div className="mt-4">
          <AiBriefing text={briefings.regions(regions[0])} />
        </div>
      )}

      {/* 미니 지도 */}
      <div className="mx-5 mt-4 rounded-2xl overflow-hidden relative" style={{ height: 120, background: '#E8EDF5' }}>
        <div className="absolute inset-0 flex items-center justify-center text-muted-foreground text-sm">
          📍 지도 미리보기
        </div>
        {regions.map((r, i) => (
          <div key={r.id} className="absolute text-xs font-bold" style={{ left: `${20 + i * 28}%`, top: `${30 + (i % 2) * 20}%`, color: COLORS.BLUE }}>
            📍{r.name.split(' ').pop()}
          </div>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
        {regions.map(r => (
          <button
            key={r.id}
            onClick={() => selectRegion(r)}
            className="w-full text-left bg-card rounded-2xl border border-border p-4 space-y-2 transition-all active:scale-[0.98]"
            style={{ boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}
          >
            <div className="flex items-start justify-between">
              <div>
                <p className="font-bold">{r.name}</p>
                {tab === 'similar' ? (
                  <p className="text-sm text-muted-foreground">
                    보증금 {formatAmount(r.midPrice)} / 월세 {r.monthlyMidPrice ? Math.round(r.monthlyMidPrice / 10_000) : '-'}만원
                  </p>
                ) : (
                  <p className="text-sm text-muted-foreground">전세 중위가 {formatAmount(r.midPrice * 1.3)}</p>
                )}
              </div>
              <span
                className="text-xs font-semibold px-2.5 py-1 rounded-full"
                style={{ background: COLORS.MINT + '33', color: COLORS.MINT }}
              >
                {tab === 'similar' ? `±${Math.round(r.surplus / 10_000)}만` : `+${formatAmount(r.surplus * 3)}`}
              </span>
            </div>
            <div className="flex gap-2 flex-wrap">
              {r.tags.map(t => (
                <span key={t} className="text-xs px-2 py-0.5 bg-muted rounded-full text-muted-foreground">{t}</span>
              ))}
            </div>
          </button>
        ))}
      </div>
      <Disclaimer />
    </MobileShell>
  );
}
