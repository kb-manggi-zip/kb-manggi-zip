import React, { useEffect, useState } from 'react';
import { useApp } from '../store';
import { COLORS, BRANCH_COLORS, BRANCH_ICONS } from '../theme';
import { MobileShell, FlowProgress, BackBtn, Disclaimer } from '../components/ui';
import AiBriefing from '../components/AiBriefing';
import { api, briefings } from '../api/client';
import { formatAmount } from '../utils/format';
import type { Region } from '../api/types';

export default function RegionList() {
  const { state, dispatch } = useApp();
  const { selectedBranch, comparison } = state;
  const [regions, setRegions] = useState<Region[]>([]);

  useEffect(() => {
    if (!selectedBranch || !comparison) return;
    const budget = comparison.branches.find(b => b.branch === selectedBranch)?.depositOrPrice || 0;
    api.regions(selectedBranch, budget).then(setRegions);
  }, [selectedBranch, comparison]);

  if (!selectedBranch || !comparison) return null;

  const branch = comparison.branches.find(b => b.branch === selectedBranch)!;
  const color = BRANCH_COLORS[selectedBranch];
  const icon = BRANCH_ICONS[selectedBranch];
  const briefText = regions.length > 0 ? briefings.regions(regions[0]) : null;

  function selectRegion(r: Region) {
    dispatch({ type: 'SELECT_REGION', regionId: r.id, region: r });
    dispatch({ type: 'NAVIGATE', screen: 'SC-07' });
  }

  return (
    <MobileShell>
      <FlowProgress current={3} />

      <div className="flex items-center gap-2 px-5 py-3 border-b-2" style={{ borderColor: color }}>
        <BackBtn onClick={() => dispatch({ type: 'NAVIGATE', screen: 'SC-03' })} />
        <span className="text-lg">{icon}</span>
        <span className="font-bold" style={{ color }}>
          {selectedBranch} · 예산 최대 {formatAmount(branch.depositOrPrice)}
        </span>
      </div>

      <div className="flex-1 overflow-y-auto">
        {/* 미니 지도 스트립 */}
        <div
          className="mx-5 mt-4 rounded-2xl overflow-hidden relative"
          style={{ height: 130, background: '#E8EDF5' }}
        >
          <div className="absolute inset-0 flex items-center justify-center text-muted-foreground text-sm">
            📍 지도 미리보기
          </div>
          {regions.map((r, i) => (
            <div
              key={r.id}
              className="absolute text-xs font-bold"
              style={{ left: `${20 + i * 28}%`, top: `${30 + (i % 2) * 20}%`, color: COLORS.BLUE }}
            >
              📍{r.name.split(' ').pop()}
            </div>
          ))}
        </div>

        {/* AI 브리핑 */}
        {briefText && (
          <div className="mt-4">
            <AiBriefing text={briefText} />
          </div>
        )}

        <div className="px-5 py-3 space-y-3">
          <h2 className="text-base font-bold text-foreground">동네 후보</h2>
          {regions.map(r => (
            <RegionCard key={r.id} region={r} color={color} onSelect={() => selectRegion(r)} />
          ))}
        </div>

        <Disclaimer />
      </div>
    </MobileShell>
  );
}

function RegionCard({ region, color, onSelect }: { region: Region; color: string; onSelect: () => void }) {
  return (
    <button
      onClick={onSelect}
      className="w-full text-left bg-card rounded-2xl border border-border p-4 space-y-3 transition-all active:scale-[0.98]"
      style={{ boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="font-bold">{region.name}</p>
          <p className="text-sm text-muted-foreground">중위가 {formatAmount(region.midPrice)}</p>
        </div>
        <span
          className="text-xs font-semibold px-2.5 py-1 rounded-full"
          style={{ background: COLORS.MINT + '33', color: COLORS.MINT }}
        >
          +{formatAmount(region.surplus)} 여유
        </span>
      </div>
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs text-muted-foreground">최근 실거래 {region.tradeCount}건</span>
        {region.tags.map(t => (
          <span key={t} className="text-xs px-2 py-0.5 bg-muted rounded-full text-muted-foreground">{t}</span>
        ))}
      </div>
      <div className="flex items-center justify-between pt-1 border-t border-border">
        <p className="text-xs text-muted-foreground">하루 살아보기 →</p>
        <span className="text-xs font-semibold" style={{ color }}>이 동네 하루 보기 →</span>
      </div>
    </button>
  );
}
