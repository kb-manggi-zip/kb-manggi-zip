import React, { useState } from 'react';
import { COLORS, BRANCH_COLORS, BRANCH_ICONS } from '../theme';
import type { Branch } from '../api/types';
import ProfileFab from './ProfileFab';

// ─── 만기 D-day 배지 (급성감 유지 — 탐색 화면에서도 "지금 결정 중"을 상기) ───
export function DdayBadge({ dday }: { dday: number }) {
  return (
    <span
      className="inline-flex items-center gap-1 text-xs font-bold px-2.5 py-1 rounded-full whitespace-nowrap"
      style={{ background: '#FDECEC', color: '#D64545' }}
      title="계약 만기까지 남은 날"
    >
      ⏰ 만기 {dday < 0 ? '지남' : `D-${dday}`}
    </span>
  );
}

// ─── Layout Shell ───────────────────────────────────────────────────────────
export function MobileShell({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={`relative flex flex-col bg-background overflow-hidden ${className}`}
      style={{ width: '100%', maxWidth: 390, minHeight: '100dvh', margin: '0 auto' }}
    >
      <ProfileFab />
      {children}
    </div>
  );
}

// ─── 만기 D-day 배너 (1층) — KB 회갈색 배경 + 크림 텍스트, 강조는 옐로우(빨강 없음) ──
// 색을 바꾸는 유일한 곳. 만기일 '확정 이후'(comparison 존재)에만 렌더한다(호출부가 조건 제어).
const _CREAM = '#FFF7E0';
const _YELLOW = '#FFBC00';
export function DdayBar({ dday, noticeDaysLeft }: { dday?: number; noticeDaysLeft?: number }) {
  const expiryPassed = dday !== undefined && dday < 0;
  const noticePassed = noticeDaysLeft !== undefined && noticeDaysLeft < 0;
  return (
    <div className="flex items-center justify-center gap-2 px-5" style={{ background: '#60584C', height: 32, fontSize: 12 }}>
      {expiryPassed ? (
        <span style={{ color: _CREAM }}>만기 <b style={{ color: _YELLOW }}>지남</b> · 계약 상태를 지금 확인하세요</span>
      ) : noticePassed ? (
        <span style={{ color: _CREAM }}>통보기한 <b style={{ color: _YELLOW }}>지남</b> · 갱신 의사를 지금 확인하세요</span>
      ) : (
        <span style={{ color: _CREAM }}>
          {dday !== undefined && <>만기 <b style={{ color: _YELLOW }}>D-{dday}</b></>}
          {dday !== undefined && noticeDaysLeft !== undefined && ' · '}
          {noticeDaysLeft !== undefined && <>통보기한 <b style={{ color: _YELLOW }}>D-{noticeDaysLeft}</b></>}
        </span>
      )}
    </div>
  );
}


// ─── Primary CTA Button ──────────────────────────────────────────────────────
export function PrimaryBtn({ children, onClick, disabled = false, className = '' }: {
  children: React.ReactNode; onClick?: () => void; disabled?: boolean; className?: string;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`w-full h-14 rounded-full font-semibold text-base transition-all duration-150 active:scale-95
        ${disabled
          ? 'bg-muted text-muted-foreground cursor-not-allowed'
          : 'text-foreground shadow-sm active:shadow-none'
        } ${className}`}
      style={{ background: disabled ? undefined : COLORS.KB_YELLOW }}
    >
      {children}
    </button>
  );
}

export function SecondaryBtn({ children, onClick, className = '' }: {
  children: React.ReactNode; onClick?: () => void; className?: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full h-14 rounded-full font-semibold text-base border border-border bg-card text-foreground
        transition-all duration-150 active:scale-95 ${className}`}
    >
      {children}
    </button>
  );
}

export function GhostBtn({ children, onClick, className = '' }: {
  children: React.ReactNode; onClick?: () => void; className?: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`text-sm text-muted-foreground underline underline-offset-2 py-2 transition-opacity active:opacity-60 ${className}`}
    >
      {children}
    </button>
  );
}

// ─── Card ────────────────────────────────────────────────────────────────────
export function Card({ children, className = '', onClick }: {
  children: React.ReactNode; className?: string; onClick?: () => void;
}) {
  return (
    <div
      onClick={onClick}
      className={`bg-card rounded-2xl p-5 shadow-sm border border-border
        ${onClick ? 'cursor-pointer transition-all duration-150 active:scale-[0.98] active:shadow-md' : ''}
        ${className}`}
      style={{ boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}
    >
      {children}
    </div>
  );
}

// ─── Selectable Card (sticky note feel) ─────────────────────────────────────
export function SelectCard({ children, selected, onClick, className = '' }: {
  children: React.ReactNode; selected: boolean; onClick: () => void; className?: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full h-full text-left rounded-2xl p-4 border-2 transition-all duration-200 flex flex-col justify-center ${className}`}
      style={{
        borderColor: selected ? COLORS.KB_YELLOW : COLORS.BORDER,
        background: selected ? COLORS.YELLOW_SURFACE : COLORS.CARD,
      }}
    >
      {children}
    </button>
  );
}

// ─── Branch Context Bar ──────────────────────────────────────────────────────
export function BranchBar({ branch }: { branch: Branch }) {
  const color = BRANCH_COLORS[branch];
  const icon = BRANCH_ICONS[branch];
  return (
    <div
      className="flex items-center gap-2 px-5 py-3 text-sm font-semibold"
      style={{ borderBottom: `3px solid ${color}` }}
    >
      <span className="text-xl">{icon}</span>
      <span style={{ color }}>{branch}</span>
    </div>
  );
}

// ─── Branch Card ─────────────────────────────────────────────────────────────
export function BranchCard({ branch, children, selected = false, className = '' }: {
  branch: Branch; children: React.ReactNode; selected?: boolean; className?: string;
}) {
  const color = BRANCH_COLORS[branch];
  return (
    <div
      className={`bg-card rounded-2xl border border-border overflow-hidden ${className}`}
      style={{
        boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
        borderLeft: `4px solid ${color}`,
        outline: selected ? `2px solid ${color}` : undefined,
      }}
    >
      {children}
    </div>
  );
}

// ─── Speech Bubble Chip ──────────────────────────────────────────────────────
export function BasisChip({ label, tip }: { label: string; tip: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative inline-block">
      <button
        onClick={() => setOpen(o => !o)}
        className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border border-border bg-muted text-muted-foreground"
      >
        💬 {label}
      </button>
      {open && (
        <div
          className="absolute bottom-full mb-2 left-0 z-50 w-44 bg-foreground text-background text-xs rounded-xl p-2.5 shadow-lg leading-relaxed"
          onClick={() => setOpen(false)}
        >
          {tip}
          <div className="absolute -bottom-1 left-4 w-2 h-2 bg-foreground rotate-45" />
        </div>
      )}
    </div>
  );
}

// ─── D-day Chip ──────────────────────────────────────────────────────────────
export function DdayChip({ dday }: { dday: number }) {
  const passed = dday < 0;
  const urgent = dday <= 30;
  return (
    <span
      className="inline-flex items-center gap-1 text-xs font-bold px-3 py-1 rounded-full"
      style={{ background: passed ? '#5C5147' : urgent ? COLORS.CORAL : COLORS.KB_YELLOW, color: passed ? '#FFE9C7' : COLORS.TEXT }}
    >
      {passed ? '만기 지남' : `D-${dday}`}
    </span>
  );
}

// ─── Disclaimer Footer ───────────────────────────────────────────────────────
export function Disclaimer() {
  return (
    <p className="text-center text-xs text-muted-foreground px-5 pb-4 pt-2 leading-relaxed">
      참고 추정치예요. 실제 조건은 심사·계약에 따라 달라져요.
    </p>
  );
}

// ─── Toast ───────────────────────────────────────────────────────────────────
export function Toast({ message, visible }: { message: string; visible: boolean }) {
  return (
    <div
      className="fixed bottom-8 left-1/2 -translate-x-1/2 z-[100] px-5 py-3 bg-foreground text-background text-sm font-medium rounded-2xl shadow-xl transition-all duration-300"
      style={{ opacity: visible ? 1 : 0, transform: `translateX(-50%) translateY(${visible ? 0 : 16}px)` }}
    >
      {message}
    </div>
  );
}

// ─── Accordion ───────────────────────────────────────────────────────────────
export function Accordion({ title, children }: { title: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border border-border rounded-2xl">
      {/* overflow-hidden을 안 씀 — 안에 BasisChip 같은 절대위치 툴팁이 있으면 잘려버려서(z-index로는 못 고침),
          대신 버튼/내용 각각에 상황별로 라운딩을 준다. */}
      <button
        onClick={() => setOpen(o => !o)}
        className={`w-full flex items-center justify-between px-4 py-3 text-sm font-medium text-foreground bg-card ${open ? 'rounded-t-2xl' : 'rounded-2xl'}`}
      >
        {title}
        <span className="transition-transform duration-200" style={{ transform: open ? 'rotate(180deg)' : 'rotate(0deg)' }}>▾</span>
      </button>
      {open && (
        <div className="px-4 pt-2 pb-4 bg-muted/50 text-sm text-muted-foreground space-y-1 rounded-b-2xl">
          {children}
        </div>
      )}
    </div>
  );
}

// ─── Step Progress ───────────────────────────────────────────────────────────
export function StepProgress({ current, total }: { current: number; total: number }) {
  return (
    <div className="flex items-center gap-2 px-5 py-3">
      <div className="flex-1 h-1.5 bg-border rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${(current / total) * 100}%`, background: COLORS.KB_YELLOW }}
        />
      </div>
      <span className="text-xs text-muted-foreground font-medium">{current}/{total}</span>
    </div>
  );
}

// ─── Back Button ─────────────────────────────────────────────────────────────
export function BackBtn({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="p-2 -ml-1 text-muted-foreground text-lg transition-opacity active:opacity-60"
    >
      ←
    </button>
  );
}

// ─── Amount Input ─────────────────────────────────────────────────────────────
export function AmountInput({
  value, onChange, placeholder = '0', label
}: { value: string; onChange: (v: string) => void; placeholder?: string; label?: string }) {
  const [focused, setFocused] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value.replace(/[^0-9]/g, '');
    onChange(raw);
  };

  const display = value ? parseInt(value).toLocaleString() : '';
  const korean = value ? toKorean(parseInt(value) * 10_000) : '';

  return (
    <div className="space-y-1">
      {label && <label className="text-sm font-medium text-muted-foreground">{label}</label>}
      <div
        className="rounded-2xl border-2 px-4 py-3 transition-colors"
        style={{ borderColor: focused ? COLORS.KB_YELLOW : COLORS.BORDER, background: '#F7F3EC' }}
      >
        <div className="flex items-center gap-1">
          <input
            type="tel"
            inputMode="numeric"
            value={display}
            onChange={handleChange}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            placeholder={placeholder}
            className="flex-1 bg-transparent text-xl font-bold text-foreground outline-none"
          />
          <span className="text-sm text-muted-foreground">만원</span>
        </div>
        {korean && (
          <p className="text-xs text-muted-foreground mt-1">{korean}</p>
        )}
      </div>
    </div>
  );
}

function toKorean(won: number): string {
  const eok = Math.floor(won / 100_000_000);
  const man = Math.round((won % 100_000_000) / 10_000);
  if (eok > 0 && man > 0) return `${eok}억 ${man.toLocaleString()}만원`;
  if (eok > 0) return `${eok}억원`;
  if (man > 0) return `${man.toLocaleString()}만원`;
  return '';
}
