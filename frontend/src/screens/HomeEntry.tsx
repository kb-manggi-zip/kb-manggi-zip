import React, { useState } from 'react';
import { useApp } from '../store';
import { COLORS, BRANCH_COLORS, BRANCH_ICONS } from '../theme';
import { MobileShell, PrimaryBtn, Toast } from '../components/ui';
import AiBriefing from '../components/AiBriefing';
import { formatDday, formatDate, formatNoticeDeadline, formatAmount } from '../utils/format';
import { PERSONAS, briefings } from '../api/client';

const DEMO_TOAST_MSG = 'P2 신혼 데모 데이터가 채워졌어요 ✓';
const TAB_TOAST_MSG = "이 데모에서는 '추천' 탭의 만기 도우미를 소개해요 🙂";
const TABS = ['추천', '매물', '시세', '청약', '뉴스'];

export default function HomeEntry() {
  const { state, dispatch } = useApp();
  const { contract, comparison } = state;
  const [toast, setToast] = useState<string | null>(null);

  const dday = contract ? formatDday(contract.expiryDate) : null;
  const noticeDeadline = contract ? formatNoticeDeadline(contract.expiryDate, 2) : null;
  const noticeDaysLeft = noticeDeadline ? Math.ceil((noticeDeadline.getTime() - Date.now()) / 86400000) : null;
  const isUrgent = noticeDaysLeft !== null && noticeDaysLeft <= 14;
  const hasData = contract !== null;

  function showToast(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(null), 2500);
  }

  function loadDemo() {
    const p2 = PERSONAS[1];
    dispatch({ type: 'SET_CONTRACT', contract: p2.contract });
    dispatch({ type: 'SET_FINANCE', finance: p2.finance });
    showToast(DEMO_TOAST_MSG);
  }

  // 재방문 revisit 텍스트: 비교표가 있을 때 D-day 기반
  const revisitText = comparison && dday !== null
    ? briefings.revisit(Math.max(0, 90 - dday))
    : null;

  return (
    <MobileShell>
      {/* KB부동산 앱 헤더 */}
      <header className="flex items-center gap-3 px-5 pt-5 pb-3">
        <div
          className="w-10 h-10 rounded-xl flex items-center justify-center text-foreground font-black text-sm"
          style={{ background: COLORS.KB_YELLOW }}
        >
          KB
        </div>
        <span className="text-lg font-bold" style={{ color: COLORS.KB_GRAY }}>KB부동산</span>
        <div className="ml-auto flex gap-3 text-xl text-muted-foreground">
          <button>🔍</button>
          <button>🔔</button>
        </div>
      </header>

      {/* 탭바 — 추천 외 탭 탭 시 토스트 */}
      <div className="flex border-b border-border px-5 text-sm">
        {TABS.map((tab, i) => (
          <button
            key={tab}
            onClick={() => i !== 0 && showToast(TAB_TOAST_MSG)}
            className="flex-1 py-2.5 font-medium transition-colors"
            style={{
              color: i === 0 ? COLORS.KB_YELLOW : COLORS.SUB,
              borderBottom: i === 0 ? `2px solid ${COLORS.KB_YELLOW}` : '2px solid transparent',
              marginBottom: -1,
            }}
          >
            {tab}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-5 space-y-4">

        {/* 만기 결정 도우미 위젯 */}
        <div
          className="rounded-3xl border border-border bg-card p-5 space-y-4 relative"
          style={{ boxShadow: '0 2px 12px rgba(0,0,0,0.07)' }}
        >
          {/* 스티커 배지 */}
          <div className="absolute top-4 right-4 text-xs font-medium px-2.5 py-1 rounded-full border border-border bg-muted text-muted-foreground">
            결정은 나중에 해도 돼요 ☁️
          </div>

          <div>
            {dday !== null ? (
              <>
                <p className="text-xs text-muted-foreground mb-1">계약 만기까지</p>
                <div className="flex items-baseline gap-2">
                  <span className="font-black text-5xl leading-none" style={{ color: COLORS.KB_GRAY }}>
                    D-{dday}
                  </span>
                  <span className="text-sm text-muted-foreground">
                    {formatDate(new Date(contract!.expiryDate))} 만기
                  </span>
                </div>
              </>
            ) : (
              <>
                <p className="text-xs text-muted-foreground mb-1">전월세 만기 결정 도우미</p>
                <p className="text-xl font-bold" style={{ color: COLORS.KB_GRAY }}>
                  눌러앉을까, 옮길까, 살까?
                </p>
                {/* 갈래 미니 라벨 */}
                <div className="flex gap-3 mt-2">
                  {(['갱신', '이사', '매매'] as const).map(b => (
                    <span key={b} className="text-xs text-muted-foreground flex items-center gap-1">
                      {BRANCH_ICONS[b]} {b}
                    </span>
                  ))}
                </div>
              </>
            )}
            <p className="text-sm text-muted-foreground mt-1">만기 전에 미리 계산해봐요</p>
          </div>

          {/* D-day 타임라인 바 */}
          {contract && noticeDeadline && (
            <div className="space-y-2">
              <div className="relative h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className="absolute left-0 h-full rounded-full"
                  style={{
                    width: `${Math.max(5, Math.min(95, (1 - dday! / 120) * 100))}%`,
                    background: isUrgent ? COLORS.CORAL : COLORS.KB_YELLOW,
                    transition: 'width 0.5s',
                  }}
                />
              </div>
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>오늘</span>
                <span style={{ color: COLORS.CORAL }}>통보기한 {formatDate(noticeDeadline)}</span>
                <span>만기 {formatDate(new Date(contract.expiryDate))}</span>
              </div>
              {isUrgent && noticeDaysLeft !== null && (
                <div
                  className="text-xs font-semibold px-3 py-1.5 rounded-xl text-white text-center"
                  style={{ background: COLORS.CORAL }}
                >
                  ⚠️ 갱신 의사 통보 기한이 {noticeDaysLeft}일 남았어요
                </div>
              )}
            </div>
          )}

          {/* 재방문 — AI 브리핑 + 비교표 미니 요약 */}
          {comparison && (
            <div className="space-y-3">
              {revisitText && (
                <AiBriefing text={revisitText} compact />
              )}
              <div className="grid grid-cols-3 gap-2">
                {comparison.branches.map(b => (
                  <div key={b.branch} className="bg-muted rounded-xl p-2 text-center">
                    <p className="text-xs text-muted-foreground">{b.branch}</p>
                    <p className="text-sm font-bold">{formatAmount(b.monthlyBurden)}/월</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          <PrimaryBtn onClick={() => dispatch({ type: 'NAVIGATE', screen: hasData ? 'SC-03' : 'SC-02' })}>
            {hasData ? '비교표 다시 보기 →' : '미리 계산해보기 →'}
          </PrimaryBtn>
        </div>

        {/* 안심 카드 */}
        <div className="rounded-2xl bg-muted px-4 py-3 text-sm text-muted-foreground leading-relaxed">
          지금 결정하지 않아도 괜찮아요 ☁️<br />
          미리 계산만 해두고, 나중에 골라도 돼요.
        </div>

        {/* 관심 지역 매물 (더미) */}
        <div>
          <p className="text-sm font-semibold text-muted-foreground mb-3">내 관심 지역 매물</p>
          <div className="space-y-3">
            {[
              { area: '마포구 합정동', type: '아파트', size: '84㎡', price: '5.3억', change: '+1.2%' },
              { area: '성북구 길음동', type: '빌라', size: '59㎡', price: '2.9억', change: '+0.8%' },
            ].map(item => (
              <div
                key={item.area}
                className="flex items-center justify-between bg-card rounded-2xl px-4 py-3 border border-border"
              >
                <div>
                  <p className="text-sm font-semibold">{item.area}</p>
                  <p className="text-xs text-muted-foreground">{item.type} · {item.size}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-bold">{item.price}</p>
                  <p className="text-xs" style={{ color: COLORS.CORAL }}>{item.change}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="px-5 pb-6 flex justify-end">
        <button
          onClick={loadDemo}
          className="text-xs text-muted-foreground border border-border rounded-full px-3 py-1.5"
        >
          🧪 데모 데이터 채우기
        </button>
      </div>

      <Toast message={toast || ''} visible={toast !== null} />
    </MobileShell>
  );
}
