import React, { useState, useRef } from 'react';
import { toPng } from 'html-to-image';
import { useApp } from '../store';
import { COLORS, BRANCH_COLORS, BRANCH_ICONS } from '../theme';
import {
  MobileShell, DdayBar, BackBtn, PrimaryBtn,
  DdayChip, BasisChip, Accordion, Disclaimer, Toast
} from '../components/ui';
import AiBriefing from '../components/AiBriefing';
import { formatAmount, formatMonthly, formatDate, ddayText } from '../utils/format';
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
  // 공통 가정은 갈래(branch)와 무관하게 같은 텍스트라 카드 3장에 반복하지 않고 여기서 한 번만 계산.
  const commonAssumptions = assumptions.filter(a => assumptionForBranch(a, '갱신') === 'common');
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
      <DdayBar dday={comparison?.dday} noticeDaysLeft={comparison?.noticeDaysLeft} />

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
        <div className="mx-5 mb-3 px-4 py-2.5 rounded-xl text-xs font-semibold flex items-center gap-1.5"
          style={{ background: '#5C5147', color: '#FFE9C7' }}>
          {noticeDaysLeft < 0 ? (
            <span>통보기한이 지났어요 — <span style={{ color: '#FF8A70' }}>묵시적 갱신</span> 가능성이 있어요. 임대인과 확인하세요.</span>
          ) : (
            <span>갱신 의사 통보기한 <b style={{ color: COLORS.KB_YELLOW }}>D-{noticeDaysLeft}</b> · <span style={{ color: '#FF8A70' }}>{formatDate(new Date(noticeDeadline))}</span>까지</span>
          )}
          <span className="ml-auto cursor-help select-none" title="만기 6~2개월 전까지 갱신 여부를 알려야 해요 (주택임대차보호법 제6조의3)">ⓘ</span>
        </div>
      )}

      {/* AI 브리핑 */}
      <AiBriefing text={briefText} />

      {/* 3갈래 미니 요약 바 — 갈래+월부담, 현재 갈래 하이라이트, 탭하면 해당 카드로 */}
      <div className="flex px-5 gap-2 mb-3 sticky top-0 z-10 py-1" style={{ background: COLORS.BG }}>
        {branches.map((b, i) => (
          <button
            key={b.branch}
            onClick={() => {
              setActiveCard(i);
              scrollRef.current?.children[i].scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
            }}
            className="flex-1 py-2 rounded-xl text-xs font-semibold transition-all leading-tight"
            style={{
              background: activeCard === i ? BRANCH_COLORS[b.branch] : COLORS.BORDER,
              color: activeCard === i ? COLORS.TEXT : COLORS.SUB,
            }}
          >
            {BRANCH_ICONS[b.branch]} {b.branch}<br />
            <span className="font-bold">{Math.round(b.monthlyBurden / 10_000)}만</span>
          </button>
        ))}
      </div>

      {/* 모든 갈래에 공통되는 가정 — 카드마다 반복하지 않고 한 번만 */}
      {commonAssumptions.length > 0 && (
        <div className="px-5 mb-3">
          <Accordion title="공통 가정">
            {commonAssumptions.map(a => (
              <p key={a} className="text-xs py-0.5">• {a}</p>
            ))}
          </Accordion>
        </div>
      )}

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
            assumptions={assumptions}
            onSelect={() => selectBranch(b.branch)}
          />
        ))}
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
          <span style={{ marginLeft: 'auto', fontSize: 12, color: COLORS.SUB }}>{ddayText(dday)}</span>
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

// 공통 가정(모든 갈래) + 갈래별 가정만 골라 보여준다(이사 카드에 매매 가정 섞임 방지).
function assumptionForBranch(a: string, branch: Branch): 'common' | 'branch' | null {
  if (/사전 가늠|기존 대출/.test(a)) return 'common';
  if (branch === '매매') return /LTV|주택구입|스트레스 DSR|생애최초|취득세/.test(a) ? 'branch' : null;
  if (branch === '갱신') return /법정 상한 5%|전월세전환|HF 공시|보증료/.test(a) ? 'branch' : null;
  if (branch === '이사') return /HF 공시|보증료/.test(a) ? 'branch' : null;
  return null;
}

function BranchCardView({
  branch, contractType, monthlyToDeposit, firstHome, assumptions, onSelect
}: { branch: BranchResult; contractType: string; monthlyToDeposit: number; firstHome?: FirstHome; assumptions: string[]; onSelect: () => void }) {
  const color = BRANCH_COLORS[branch.branch];
  const icon = BRANCH_ICONS[branch.branch];
  const branchAssumptions = assumptions.map(a => [a, assumptionForBranch(a, branch.branch)] as const).filter(([, k]) => k);

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
        {/* monthlyBurden은 이미 반환보증료 포함(=실질). 이중으로 더하지 않고 이자/월세 + 보증료로 분해 표시. */}
        <p className="text-xs text-muted-foreground">실질 월 부담 <span className="opacity-70">(반환보증료 포함)</span></p>
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-bold text-foreground">
            {Math.round(branch.monthlyBurden / 10_000)}만원
          </span>
        </div>
        {branch.guaranteeMonthly > 0 && (
          <p className="text-xs text-muted-foreground mt-0.5">
            이자·월세 {formatMonthly(branch.monthlyBurden - branch.guaranteeMonthly)} + 반환보증료 {formatMonthly(branch.guaranteeMonthly)} 포함
          </p>
        )}
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

      {/* 대출 한도가 실제로 바뀔 수 있는 정보라 접지 않고 항상 보이게 유지 */}
      {branch.branch === '매매' && firstHome === '모름' && (
        <div className="mx-5 mt-3 px-3 py-2 rounded-lg" style={{ background: COLORS.YELLOW_SURFACE }}>
          <p className="text-[11px]" style={{ color: COLORS.KB_GRAY }}>
            💡 생애최초라면 LTV 70%까지 가능해 한도가 더 늘어날 수 있어요
          </p>
        </div>
      )}

      {/* 접힘: 리스크·대비 — 항목별 1:1 대응은 아니라서(예: 매매의 화재보험이 자산가치 변동 리스크를
          직접 상쇄하진 않음) 화살표로 짝짓지 않고, 각 목록 제목을 문장형으로 써서 관계만 드러낸다. */}
      <div className="px-5 py-2 border-b border-border">
        <Accordion title="리스크는 없나요?">
          <div>
            <p className="text-muted-foreground font-medium mb-1">⚠️ 이런 리스크가 있을 수 있어요</p>
            {branch.risks.map(r => <p key={r} className="text-xs py-0.5">• {r}</p>)}
            {branch.uncertainty && (
              <p className="mt-1 text-xs text-muted-foreground italic">※ {branch.uncertainty}</p>
            )}
          </div>
          <div className="mt-2">
            <p className="text-muted-foreground font-medium mb-1">🛡 이렇게 대비해요</p>
            {branch.cares.map(c => <p key={c} className="text-xs py-0.5">• {c}</p>)}
          </div>
        </Accordion>
      </div>

      {/* 접힘: 근거·가정 (feature 인용 + 근거칩 + 계산 가정) */}
      <div className="px-5 py-2">
        <Accordion title="어떻게 계산했나요?">
          <p className="text-xs italic mb-2">"{branch.feature}"</p>
          {basisChips.length > 0 && (
            <div className="mb-2">
              <p className="text-muted-foreground font-medium mb-1">📎 이 계산의 근거예요</p>
              <div className="flex gap-1 flex-wrap">
                {basisChips.map(c => <BasisChip key={c.label} label={c.label} tip={c.tip} />)}
              </div>
            </div>
          )}
          {/* 모든 갈래 공통 가정은 카드마다 반복하지 않고 카드 스와이프 위에 한 번만 보여줌 */}
          {branchAssumptions.some(([, k]) => k === 'branch') && (
            <div>
              <p className="text-muted-foreground font-medium mb-1">📝 이런 가정으로 계산했어요</p>
              {branchAssumptions.filter(([, k]) => k === 'branch').map(([a]) => (
                <p key={a} className="text-xs py-0.5">• {a}</p>
              ))}
            </div>
          )}
        </Accordion>
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
