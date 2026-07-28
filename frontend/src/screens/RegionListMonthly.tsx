import React, { useEffect, useState, useMemo } from 'react';
import { useApp } from '../store';
import type { Screen } from '../store';
import { COLORS } from '../theme';
import { MobileShell, DdayBar, BackBtn, Disclaimer } from '../components/ui';
import AiBriefing from '../components/AiBriefing';
import { api, briefings } from '../api/client';
import { formatAmount } from '../utils/format';
import { RegionCard, foldedCommonReasons, commonGuName } from './RegionList';
import type { Region } from '../api/types';

type Tab = 'similar' | 'upgrade';

export default function RegionListMonthly() {
  const { state, dispatch } = useApp();
  const [tab, setTab] = useState<Tab>('similar');
  const [regions, setRegions] = useState<Region[]>([]);

  useEffect(() => {
    api.regionsMonthly(state.contract?.housingType, state.contract?.preferredArea, state.finance?.household).then(setRegions);
  }, [state.contract?.housingType, state.contract?.preferredArea, state.finance?.household]);

  function selectRegion(r: Region, screen: Screen) {
    dispatch({ type: 'SELECT_REGION', regionId: r.id, region: r });
    dispatch({ type: 'NAVIGATE', screen });
  }

  // 전세 카드와 동일한 구성 적용(L2): 구 폴백 동일값 접기 + 재택 확정 시 통근 격하
  const commonReasons = useMemo(() => foldedCommonReasons(regions), [regions]);
  const commonGu = commonGuName(regions);
  const deemphasizeCommute = (state.contract?.noteAdjust?.commute ?? 1) < 0.95;

  return (
    <MobileShell>
      <DdayBar dday={state.comparison?.dday} noticeDaysLeft={state.comparison?.noticeDaysLeft} />

      <div className="flex items-center gap-2 px-5 py-2 border-b-2" style={{ borderColor: COLORS.BLUE }}>
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
        <div className="mx-5 mt-3 px-4 py-2.5 bg-muted rounded-xl text-xs text-muted-foreground space-y-1">
          <p>🛡 전세 전환 시 반환보증 가입을 함께 확인하세요.</p>
          {/* P5: 발품 넘김 — 시세 기준임을 명시(실매물·집주인 확인은 발품 영역) */}
          <p>📍 여기 숫자는 <b>실거래 시세 기준</b>이에요. 실제 매물·집주인 의사는 확인이 필요해요 — 카드의 KB부동산에서 이어보세요.</p>
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
        {/* 구 폴백 동일값 접기(J4 패리티) */}
        {commonReasons.length > 0 && (
          <div className="rounded-2xl border p-3 text-xs" style={{ borderColor: COLORS.BLUE + '44', background: COLORS.BLUE + '0A' }}>
            <p className="font-semibold mb-1" style={{ color: COLORS.BLUE }}>
              {commonGu ? `${regions.length}개 동네 모두 ${commonGu} — 아래는 구 기준 공통값이에요` : '아래는 구 기준 공통값이에요'}
            </p>
            {commonReasons.map((r, i) => <p key={i} style={{ color: COLORS.SUB }}>· {r}</p>)}
            <p className="mt-1 text-[11px]" style={{ color: COLORS.SUB }}>동 단위 데이터는 순차 수집 예정 · 아래 카드엔 동별로 다른 값만</p>
          </div>
        )}
        {regions.map(r => (
          <RegionCard
            key={r.id}
            region={r}
            color={COLORS.BLUE}
            onSelect={() => selectRegion(r, 'SC-09')}
            onExperience={() => selectRegion(r, 'SC-07')}
            deemphasizeCommute={deemphasizeCommute}
            hiddenReasons={commonReasons}
            subtitle={tab === 'similar'
              ? `보증금 ${formatAmount(r.midPrice)} / 월세 ${r.monthlyMidPrice ? Math.round(r.monthlyMidPrice / 10_000) : '-'}만원`
              : `전세 중위가 ${formatAmount(r.midPrice * 1.3)}`}
          />
        ))}
      </div>
      <Disclaimer />
    </MobileShell>
  );
}
