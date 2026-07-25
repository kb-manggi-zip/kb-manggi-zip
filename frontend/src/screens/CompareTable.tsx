import React, { useState, useRef } from 'react';
import { toPng } from 'html-to-image';
import { useApp } from '../store';
import { COLORS, BRANCH_COLORS, BRANCH_ICONS } from '../theme';
import {
  MobileShell, FlowProgress, BackBtn, PrimaryBtn,
  DdayChip, BasisChip, Accordion, Disclaimer, Toast
} from '../components/ui';
import AiBriefing from '../components/AiBriefing';
import { formatAmount, formatMonthly, formatDate } from '../utils/format';
import { briefings } from '../api/client';
import type { BranchResult, Branch, FirstHome } from '../api/types';

export default function CompareTable() {
  const { state, dispatch } = useApp();
  const { comparison, contract, finance } = state;
  const [activeCard, setActiveCard] = useState(0);
  const [toast, setToast] = useState<string | null>(null);
  const [saveMenuOpen, setSaveMenuOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const shareRef = useRef<HTMLDivElement>(null);

  if (!comparison || !contract) {
    dispatch({ type: 'NAVIGATE', screen: 'SC-01' });
    return null;
  }

  const { branches, dday, noticeDaysLeft, noticeDeadline, assumptions } = comparison;
  const name = finance?.household === '신혼' ? '신혼 가구' : '나';
  // 분석 에이전트(narrate 노드)가 만든 통역을 재사용(중복 LLM 호출 없음). 없으면 로컬 템플릿.
  const briefText = state.briefing?.trim() ? state.briefing : briefings.compare(comparison, name);

  function showToast(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(null), 2500);
  }

  function handleSave() {
    localStorage.setItem('kb_comparison', JSON.stringify(comparison));
    setSaveMenuOpen(false);
    showToast('비교표를 저장했어요 🔖');
  }

  async function handleImageSave() {
    setSaveMenuOpen(false);
    if (!shareRef.current) return;
    try {
      const dataUrl = await toPng(shareRef.current, { cacheBust: true, pixelRatio: 2 });
      const a = document.createElement('a');
      a.href = dataUrl;
      a.download = 'kb_만기상담소_비교표.png';
      a.click();
      showToast('이미지로 저장했어요 📸');
    } catch {
      showToast('이미지 저장에 실패했어요. 다시 시도해주세요.');
    }
  }

  function selectBranch(branch: Branch) {
    dispatch({ type: 'SELECT_BRANCH', branch });
    if (branch === '갱신') dispatch({ type: 'NAVIGATE', screen: 'SC-06' });
    else dispatch({ type: 'NAVIGATE', screen: 'SC-04' });
  }

  return (
    <MobileShell>
      <FlowProgress current={2} />

      <div className="flex items-center justify-between px-4 py-2">
        <BackBtn onClick={() => dispatch({ type: 'NAVIGATE', screen: 'SC-02' })} />
        <div className="relative">
          <button onClick={() => setSaveMenuOpen(o => !o)} className="text-xl p-2">🔖</button>
          {saveMenuOpen && (
            <div className="absolute right-0 top-10 z-50 bg-card border border-border rounded-2xl shadow-lg overflow-hidden w-40">
              <button onClick={handleSave} className="w-full text-left px-4 py-3 text-sm hover:bg-muted">📋 목록에 저장</button>
              <button onClick={handleImageSave} className="w-full text-left px-4 py-3 text-sm hover:bg-muted border-t border-border">📸 이미지로 저장</button>
            </div>
          )}
        </div>
      </div>

      {/* 타이틀 — "세 가지 길" 제거 */}
      <div className="px-5 pb-2 flex items-center justify-between">
        <h1 className="text-xl font-bold" style={{ color: COLORS.KB_GRAY }}>
          {name}님, 눌러앉을까 옮길까 살까?
        </h1>
        <DdayChip dday={dday} />
      </div>

      {noticeDaysLeft !== null && noticeDaysLeft <= 30 && (
        <div className="mx-5 mb-3 px-4 py-2 rounded-xl text-xs font-semibold text-white"
          style={{ background: COLORS.CORAL }}>
          ⚠️ 갱신 의사 통보 기한이 {noticeDaysLeft}일 남았어요 ({formatDate(new Date(noticeDeadline))})
        </div>
      )}

      {/* AI 브리핑 */}
      <AiBriefing text={briefText} />

      {/* 카드 탭 인디케이터 */}
      <div className="flex px-5 gap-2 mb-3">
        {branches.map((b, i) => (
          <button
            key={b.branch}
            onClick={() => {
              setActiveCard(i);
              scrollRef.current?.children[i].scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
            }}
            className="flex-1 py-2 rounded-xl text-xs font-semibold transition-all"
            style={{
              background: activeCard === i ? BRANCH_COLORS[b.branch] : COLORS.BORDER,
              color: activeCard === i ? COLORS.TEXT : COLORS.SUB,
            }}
          >
            {BRANCH_ICONS[b.branch]} {b.branch}
          </button>
        ))}
      </div>

      {/* 카드 스와이프 영역 */}
      <div
        ref={scrollRef}
        className="flex gap-4 px-5 pb-4 overflow-x-auto snap-x snap-mandatory"
        style={{ scrollbarWidth: 'none' }}
        onScroll={e => {
          const el = e.currentTarget;
          const idx = Math.round(el.scrollLeft / el.offsetWidth);
          setActiveCard(idx);
        }}
      >
        {branches.map(b => (
          <BranchCardView
            key={b.branch}
            branch={b}
            contractType={contract.type}
            monthlyToDeposit={comparison.monthlyToDeposit}
            firstHome={finance?.firstHome}
            onSelect={() => selectBranch(b.branch)}
          />
        ))}
      </div>

      {/* 가정 아코디언 */}
      <div className="px-5 pb-4">
        <Accordion title="이 계산의 가정 보기">
          {assumptions.map(a => <p key={a} className="text-xs py-0.5">• {a}</p>)}
        </Accordion>
      </div>

      <Disclaimer />
      <Toast message={toast || ''} visible={toast !== null} />

      {/* 공유용 숨김 DOM — 이미지 캡처용 */}
      <div className="fixed -top-[9999px] left-0" aria-hidden>
        <ShareCard ref={shareRef} branches={branches} name={name} dday={dday} />
      </div>
    </MobileShell>
  );
}

// ─── 공유 카드 (이미지 캡처용) ────────────────────────────────────────────
const ShareCard = React.forwardRef<HTMLDivElement, { branches: BranchResult[]; name: string; dday: number }>(
  ({ branches, name, dday }, ref) => (
    <div
      ref={ref}
      style={{
        width: 540,
        background: COLORS.BG,
        fontFamily: "'Pretendard', sans-serif",
        padding: 32,
        borderRadius: 24,
      }}
    >
      <div style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
          <div style={{ background: COLORS.KB_YELLOW, borderRadius: 10, width: 32, height: 32, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 900, fontSize: 11 }}>KB</div>
          <span style={{ fontWeight: 700, color: COLORS.KB_GRAY }}>KB 만기상담소</span>
          <span style={{ marginLeft: 'auto', fontSize: 12, color: COLORS.SUB }}>D-{dday}</span>
        </div>
        <p style={{ fontSize: 16, fontWeight: 700, color: COLORS.KB_GRAY, margin: 0 }}>{name}님 비교 결과</p>
      </div>
      <div style={{ display: 'flex', gap: 12 }}>
        {branches.map(b => {
          const color = BRANCH_COLORS[b.branch];
          return (
            <div key={b.branch} style={{ flex: 1, background: '#fff', borderRadius: 16, borderLeft: `4px solid ${color}`, padding: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
                <span style={{ fontSize: 18 }}>{BRANCH_ICONS[b.branch]}</span>
                <span style={{ fontWeight: 700, color, fontSize: 13 }}>{b.branch}</span>
              </div>
              <p style={{ fontSize: 11, color: COLORS.SUB, margin: '0 0 4px' }}>월 부담</p>
              <p style={{ fontSize: 18, fontWeight: 700, color: COLORS.TEXT, margin: '0 0 4px' }}>
                {Math.round(b.monthlyBurden / 10_000)}만원
              </p>
              <p style={{ fontSize: 10, color: COLORS.SUB, margin: 0 }}>{b.feature}</p>
            </div>
          );
        })}
      </div>
      <p style={{ fontSize: 10, color: COLORS.SUB, textAlign: 'center', marginTop: 16 }}>
        KB 만기상담소 · 참고 추정치
      </p>
    </div>
  )
);

function BranchCardView({
  branch, contractType, monthlyToDeposit, firstHome, onSelect
}: { branch: BranchResult; contractType: string; monthlyToDeposit: number; firstHome?: FirstHome; onSelect: () => void }) {
  const color = BRANCH_COLORS[branch.branch];
  const icon = BRANCH_ICONS[branch.branch];

  // 매매 근거 칩: LTV / KB한도 / 디딤돌 3개 + 출처 툴팁 (스트레스 DSR은 가정 아코디언으로)
  const basisChips =
    branch.branch === '매매'
      ? branch.basis.flatMap(b => {
          if (b.startsWith('규제지역 LTV')) return [{ label: b, tip: "출처: 금융위 '26 가계부채 관리방안" }];
          if (b === 'KB 한도 3억') return [{ label: b, tip: '출처: KB 2026.7.10 시행' }];
          if (b === '디딤돌 혼합') return [{ label: '디딤돌 2.85% 혼합', tip: '출처: 주택도시기금' }];
          return [];
        })
      : branch.basis.map(b => ({ label: b, tip: b }));

  return (
    <div
      className="flex-none snap-center bg-card rounded-3xl border border-border overflow-hidden"
      style={{
        width: 'calc(100vw - 60px)',
        maxWidth: 330,
        boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
        borderLeft: `4px solid ${color}`,
      }}
    >
      <div className="px-5 pt-5 pb-3 flex items-center gap-2">
        <span className="text-2xl">{icon}</span>
        <div>
          <span className="text-sm font-bold" style={{ color }}>{branch.branch}</span>
          <p className="text-xs text-muted-foreground">{branch.headline}</p>
        </div>
      </div>

      <div className="px-5 pb-3 border-b border-border">
        <p className="text-xs text-muted-foreground">월 부담</p>
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-bold text-foreground">
            {Math.round(branch.monthlyBurden / 10_000)}만원
          </span>
          {branch.guaranteeMonthly > 0 && (
            <span className="text-xs text-muted-foreground">
              +보증료 {Math.round(branch.guaranteeMonthly / 10_000)}만
            </span>
          )}
        </div>
        <p className="text-xs text-muted-foreground mt-0.5">
          실질 월 부담: {formatMonthly(branch.monthlyBurden + branch.guaranteeMonthly)}
        </p>
      </div>

      <div className="px-5 py-3 space-y-2 text-sm border-b border-border">
        <Row label={branch.branch === '매매' ? '집값 상한' : '보증금'} value={formatAmount(branch.depositOrPrice)} />
        {branch.loanAmount > 0 && (
          <Row label="필요 대출" value={formatAmount(branch.loanAmount)}
            chip={<BasisChip label="기준" tip="LTV·DSR 기준 추정치예요" />} />
        )}
        {branch.oneTimeCost > 0 && (
          <Row label="일회성 비용" value={formatAmount(branch.oneTimeCost)}
            chip={<BasisChip label="산출" tip="이사비 + 중개수수료 기준" />} />
        )}
        {contractType === '월세' && monthlyToDeposit > 0 && branch.branch === '갱신' && (
          <Row label="월세→보증금 환산" value={formatAmount(monthlyToDeposit)}
            chip={<BasisChip label="환산율" tip="전월세전환율 5.5% 기준" />} />
        )}
      </div>

      <div className="px-5 py-3 bg-muted/40 space-y-2 text-xs border-b border-border">
        <div>
          <p className="text-muted-foreground font-medium mb-1">⚠️ 리스크</p>
          {branch.risks.map(r => <p key={r}>• {r}</p>)}
          {branch.uncertainty && (
            <p className="mt-1 text-muted-foreground italic">※ {branch.uncertainty}</p>
          )}
          {branch.branch === '매매' && firstHome === '모름' && (
            <div className="mt-2 px-2 py-1.5 rounded-lg" style={{ background: COLORS.YELLOW_SURFACE }}>
              <p className="text-[11px]" style={{ color: COLORS.KB_GRAY }}>
                💡 생애최초라면 LTV 70%까지 가능해 한도가 더 늘어날 수 있어요
              </p>
            </div>
          )}
        </div>
        <div>
          <p className="text-muted-foreground font-medium mb-1">🛡 대비</p>
          {branch.cares.map(c => <p key={c}>• {c}</p>)}
        </div>
      </div>

      <div className="px-5 py-3 flex items-center justify-between">
        <p className="text-xs text-muted-foreground italic">"{branch.feature}"</p>
        <div className="flex gap-1 flex-wrap justify-end">
          {basisChips.map(c => <BasisChip key={c.label} label={c.label} tip={c.tip} />)}
        </div>
      </div>

      <div className="px-5 pb-5">
        <button
          onClick={onSelect}
          className="w-full h-11 rounded-full text-sm font-semibold border transition-all active:scale-95"
          style={{ borderColor: color, color, background: 'transparent' }}
        >
          {branch.branch === '갱신' ? '눌러앉기 살펴보기 →' : branch.branch === '이사' ? '옮기기 살펴보기 →' : '사기 살펴보기 →'}
        </button>
      </div>
    </div>
  );
}

function Row({ label, value, chip }: { label: string; value: string; chip?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-muted-foreground">{label}</span>
      <div className="flex items-center gap-1">
        <span className="font-semibold">{value}</span>
        {chip}
      </div>
    </div>
  );
}
