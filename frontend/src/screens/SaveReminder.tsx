import React, { useEffect, useState } from 'react';
import { useApp } from '../store';
import { COLORS, BRANCH_COLORS, BRANCH_ICONS } from '../theme';
import { MobileShell, FlowProgress, PrimaryBtn, Disclaimer } from '../components/ui';
import { formatAmount, formatDate, formatDday } from '../utils/format';

export default function SaveReminder() {
  const { state, dispatch } = useApp();
  const { comparison, contract, selectedBranch, reservationDate, reminderOn } = state;
  const [checked, setChecked] = useState(false);

  const hasReservation = !!reservationDate;
  const dday = contract ? formatDday(contract.expiryDate) : null;

  const reminderDate = contract
    ? new Date(new Date(contract.expiryDate).getTime() - 14 * 86400000)
    : null;

  useEffect(() => {
    const t = setTimeout(() => setChecked(true), 600);
    return () => clearTimeout(t);
  }, []);

  return (
    <MobileShell>
      <FlowProgress current={6} />

      <div className="flex-1 overflow-y-auto px-5 py-6 space-y-5">
        {/* 완료 체크 애니메이션 */}
        <div className="flex flex-col items-center pt-4 pb-2">
          <div
            className="w-20 h-20 rounded-full flex items-center justify-center text-3xl transition-all duration-700"
            style={{
              background: checked ? COLORS.MINT : COLORS.BORDER,
              transform: checked ? 'scale(1)' : 'scale(0.8)',
              boxShadow: checked ? `0 8px 32px ${COLORS.MINT}44` : 'none',
            }}
          >
            {checked ? '✓' : ''}
          </div>
          <h1 className="text-xl font-bold mt-5 text-center" style={{ color: COLORS.KB_GRAY }}>
            {hasReservation ? '예약이 완료됐어요!' : '비교표를 저장했어요!'}
          </h1>
          <p className="text-sm text-muted-foreground mt-2 text-center">
            아직 결정 전이어도 괜찮아요 🌤
          </p>
          {dday && (
            <p className="text-sm text-muted-foreground mt-1">만기 D-{dday}에 다시 만나요 👋</p>
          )}
        </div>

        {/* 예약 요약 */}
        {hasReservation && reservationDate && (
          <div
            className="rounded-2xl p-4 border border-border"
            style={{ background: COLORS.YELLOW_SURFACE }}
          >
            <p className="text-xs text-muted-foreground mb-1">예약 일정</p>
            <p className="font-semibold">
              {(() => {
                const d = new Date(reservationDate);
                const days = ['일', '월', '화', '수', '목', '금', '토'];
                return `${d.getMonth() + 1}/${d.getDate()}(${days[d.getDay()]}) KB 금융 상담`;
              })()}
            </p>
          </div>
        )}

        {/* 비교표 미니 요약 썸네일 */}
        {comparison && (
          <div className="space-y-2">
            <p className="text-sm font-semibold text-muted-foreground">비교 요약</p>
            <div className="grid grid-cols-3 gap-2">
              {comparison.branches.map(b => {
                const color = BRANCH_COLORS[b.branch];
                const icon = BRANCH_ICONS[b.branch];
                return (
                  <div
                    key={b.branch}
                    className="rounded-2xl p-3 text-center border-l-4"
                    style={{ borderColor: color, background: COLORS.CARD, boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}
                  >
                    <p className="text-base mb-1">{icon}</p>
                    <p className="text-xs font-medium" style={{ color }}>{b.branch}</p>
                    <p className="text-sm font-bold mt-1">{Math.round(b.monthlyBurden / 10_000)}만</p>
                    <p className="text-xs text-muted-foreground">월 부담</p>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* 리마인더 토글 */}
        {reminderDate && (
          <div className="bg-card rounded-2xl border border-border p-4 flex items-center gap-4">
            <div className="text-xl" style={{ color: COLORS.CORAL }}>📅</div>
            <div className="flex-1">
              <p className="text-sm font-semibold">갱신 통보 기한 2주 전 알림</p>
              <p className="text-xs text-muted-foreground mt-0.5">
                {formatDate(reminderDate)} 알림 예정
              </p>
            </div>
            <button
              onClick={() => dispatch({ type: 'TOGGLE_REMINDER' })}
              className="relative w-12 h-6 rounded-full transition-all duration-300"
              style={{ background: reminderOn ? COLORS.CORAL : COLORS.BORDER }}
            >
              <span
                className="absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-all duration-300"
                style={{ left: reminderOn ? 24 : 2 }}
              />
            </button>
          </div>
        )}

        {/* 선택 갈래 (있을 경우) */}
        {selectedBranch && (
          <div className="bg-muted rounded-2xl px-4 py-3 text-sm text-muted-foreground">
            선택한 길: {BRANCH_ICONS[selectedBranch]} {selectedBranch}
            <span className="ml-1 text-xs">(아직 확정이 아니에요)</span>
          </div>
        )}
      </div>

      <div className="px-5 pb-8 pt-3 space-y-2">
        {selectedBranch && (
          <button
            onClick={() => dispatch({ type: 'NAVIGATE', screen: 'SC-13' })}
            className="w-full py-3 rounded-2xl border font-semibold text-sm"
            style={{ borderColor: COLORS.KB_YELLOW, background: COLORS.YELLOW_SURFACE, color: COLORS.TEXT }}
          >
            📄 만기 결정 리포트 보기
          </button>
        )}
        <PrimaryBtn onClick={() => dispatch({ type: 'NAVIGATE', screen: 'SC-01' })}>
          처음으로
        </PrimaryBtn>
      </div>

      <Disclaimer />
    </MobileShell>
  );
}
