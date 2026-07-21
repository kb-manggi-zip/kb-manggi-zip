import React, { useState } from 'react';
import { useApp } from '../store';
import { COLORS, BRANCH_COLORS, BRANCH_ICONS } from '../theme';
import { MobileShell, FlowProgress, PrimaryBtn, GhostBtn } from '../components/ui';
import { api } from '../api/client';

function buildCalendar(year: number, month: number): (number | null)[][] {
  const firstDay = new Date(year, month, 1).getDay(); // 0=Sun
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells: (number | null)[] = Array(firstDay).fill(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);
  while (cells.length % 7 !== 0) cells.push(null);
  const weeks: (number | null)[][] = [];
  for (let i = 0; i < cells.length; i += 7) weeks.push(cells.slice(i, i + 7));
  return weeks;
}

const DAY_LABELS = ['일', '월', '화', '수', '목', '금', '토'];

function formatSelectedLabel(year: number, month: number, day: number): string {
  const d = new Date(year, month, day);
  const dayName = DAY_LABELS[d.getDay()];
  return `${month + 1}월 ${day}일 (${dayName}) 상담 희망`;
}

export default function ReservationSheet() {
  const { state, dispatch } = useApp();
  const { selectedBranch } = state;

  const today = new Date();
  const [viewYear, setViewYear] = useState(today.getFullYear());
  const [viewMonth, setViewMonth] = useState(today.getMonth());
  const [selectedDay, setSelectedDay] = useState<number | null>(null);
  const [confirming, setConfirming] = useState(false);

  if (!selectedBranch) return null;
  const color = BRANCH_COLORS[selectedBranch];
  const icon = BRANCH_ICONS[selectedBranch];

  const weeks = buildCalendar(viewYear, viewMonth);

  function isDisabled(day: number): boolean {
    const d = new Date(viewYear, viewMonth, day);
    const todayMidnight = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    return d <= todayMidnight || d.getDay() === 0 || d.getDay() === 6;
  }

  function prevMonth() {
    if (viewMonth === 0) { setViewYear(y => y - 1); setViewMonth(11); }
    else setViewMonth(m => m - 1);
    setSelectedDay(null);
  }

  function nextMonth() {
    if (viewMonth === 11) { setViewYear(y => y + 1); setViewMonth(0); }
    else setViewMonth(m => m + 1);
    setSelectedDay(null);
  }

  async function confirm() {
    if (!selectedDay) return;
    setConfirming(true);
    const iso = `${viewYear}-${String(viewMonth + 1).padStart(2, '0')}-${String(selectedDay).padStart(2, '0')}`;
    try {
      await api.reservation({ branch: selectedBranch!, date: iso, productName: '금융 패키지 상담' });
      dispatch({ type: 'SET_RESERVATION', date: iso });
      dispatch({ type: 'NAVIGATE', screen: 'SC-11' });
    } finally {
      setConfirming(false);
    }
  }

  return (
    <MobileShell>
      <FlowProgress current={5} />

      <div className="flex-1 overflow-y-auto">
        <div className="flex flex-col items-center pt-8 pb-4 px-5">
          <div className="w-10 h-1 bg-border rounded-full mb-6" />
          <h1 className="text-xl font-bold text-center" style={{ color: COLORS.KB_GRAY }}>상담 예약하기</h1>
          <p className="text-sm text-muted-foreground mt-1 text-center">
            영업 연락이 아닌, 요청하신 상담 연결이에요
          </p>
        </div>

        {/* 갈래·상품 요약 */}
        <div className="mx-5 mb-5 p-4 rounded-2xl border border-border bg-muted/40">
          <p className="text-xs text-muted-foreground mb-1">예약 상담 대상</p>
          <div className="flex items-center gap-2">
            <span className="text-lg">{icon}</span>
            <span className="font-semibold" style={{ color }}>{selectedBranch} · KB 금융 패키지</span>
          </div>
        </div>

        {/* 캘린더 */}
        <div className="mx-5 bg-card rounded-2xl border border-border overflow-hidden">
          {/* 헤더 */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-border">
            <button
              onClick={prevMonth}
              className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-muted transition-colors text-muted-foreground"
            >
              ◀
            </button>
            <span className="font-semibold text-foreground">
              {viewYear}년 {viewMonth + 1}월
            </span>
            <button
              onClick={nextMonth}
              className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-muted transition-colors text-muted-foreground"
            >
              ▶
            </button>
          </div>

          {/* 요일 헤더 */}
          <div className="grid grid-cols-7 border-b border-border">
            {DAY_LABELS.map((d, i) => (
              <div
                key={d}
                className="py-2 text-center text-xs font-medium"
                style={{ color: i === 0 ? COLORS.CORAL : i === 6 ? COLORS.BLUE : COLORS.SUB }}
              >
                {d}
              </div>
            ))}
          </div>

          {/* 날짜 그리드 */}
          <div className="p-2">
            {weeks.map((week, wi) => (
              <div key={wi} className="grid grid-cols-7">
                {week.map((day, di) => {
                  if (!day) return <div key={di} />;
                  const disabled = isDisabled(day);
                  const selected = selectedDay === day;
                  const isWeekend = di === 0 || di === 6;
                  return (
                    <button
                      key={di}
                      onClick={() => !disabled && setSelectedDay(day)}
                      disabled={disabled}
                      className="flex items-center justify-center h-9 text-sm transition-all"
                    >
                      <span
                        className="w-8 h-8 flex items-center justify-center rounded-full font-medium transition-all"
                        style={{
                          background: selected ? COLORS.KB_YELLOW : 'transparent',
                          color: selected
                            ? COLORS.TEXT
                            : disabled
                            ? '#C8C4BB'
                            : isWeekend
                            ? COLORS.SUB
                            : COLORS.TEXT,
                          fontWeight: selected ? 700 : 500,
                        }}
                      >
                        {day}
                      </span>
                    </button>
                  );
                })}
              </div>
            ))}
          </div>
        </div>

        {/* 선택 확인 라벨 */}
        {selectedDay && (
          <div
            className="mx-5 mt-4 px-4 py-3 rounded-2xl text-sm font-semibold"
            style={{ background: color + '1A', color }}
          >
            📅 {formatSelectedLabel(viewYear, viewMonth, selectedDay)}
          </div>
        )}
      </div>

      <div className="px-5 pb-8 pt-4 space-y-3">
        <PrimaryBtn onClick={confirm} disabled={!selectedDay || confirming}>
          {confirming ? '예약 중...' : '예약 확정'}
        </PrimaryBtn>
        <GhostBtn onClick={() => dispatch({ type: 'NAVIGATE', screen: 'SC-09' })} className="w-full text-center">
          나중에 할게요
        </GhostBtn>
      </div>
    </MobileShell>
  );
}
