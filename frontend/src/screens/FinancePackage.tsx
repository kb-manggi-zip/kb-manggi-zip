import React, { useEffect, useState } from 'react';
import { useApp } from '../store';
import { COLORS, BRANCH_COLORS, BRANCH_ICONS } from '../theme';
import { MobileShell, DdayBar, BackBtn, PrimaryBtn, SecondaryBtn, BasisChip, Disclaimer, Toast } from '../components/ui';
import AiBriefing from '../components/AiBriefing';
import { api, briefings } from '../api/client';
import { formatAmount } from '../utils/format';
import { officialProductUrl } from '../utils/external';
import type { ProductsResponse } from '../api/types';

// Q2: 상품명 → 공식 페이지가 매칭되면 외부 링크로, 없으면 텍스트로.
function ProductName({ name, className }: { name: string; className?: string }) {
  const url = officialProductUrl(name);
  if (!url) return <span className={className}>{name}</span>;
  return (
    <a href={url} target="_blank" rel="noopener noreferrer" className={`${className ?? ''} underline underline-offset-2`}>
      {name} ↗
    </a>
  );
}

// 상품 로딩 스켈레톤 — 오류 오인 방지용 '불러오는 중' 표시(백엔드 상품 사유 LLM 대기 구간).
function FinanceSkeleton({ color }: { color: string }) {
  return (
    <div className="space-y-4 animate-pulse" aria-busy="true" aria-label="상품 불러오는 중">
      <div className="h-3 w-3/5 rounded bg-muted" />
      <div className="rounded-3xl border-2 p-5 space-y-3" style={{ borderColor: color + '55' }}>
        <div className="h-5 w-1/2 rounded bg-muted" />
        <div className="h-3 w-3/4 rounded bg-muted" />
        <div className="h-16 w-full rounded-xl bg-muted" />
        <div className="grid grid-cols-2 gap-3">
          <div className="h-12 rounded-xl bg-muted" />
          <div className="h-12 rounded-xl bg-muted" />
        </div>
      </div>
      <div className="rounded-2xl border border-border p-5 space-y-2">
        <div className="h-4 w-1/3 rounded bg-muted" />
        <div className="h-3 w-2/3 rounded bg-muted" />
      </div>
      <p className="text-xs text-center text-muted-foreground">맞춤 상품을 불러오는 중이에요…</p>
    </div>
  );
}

export default function FinancePackage() {
  const { state, dispatch } = useApp();
  const { selectedBranch, comparison, prevScreen } = state;
  const [products, setProducts] = useState<ProductsResponse | null>(null);
  const [toastVisible, setToastVisible] = useState(false);
  const [toastMsg, setToastMsg] = useState('');

  useEffect(() => {
    if (!selectedBranch || !comparison) return;
    api.products(selectedBranch, comparison).then(setProducts);
  }, [selectedBranch, comparison]);

  if (!selectedBranch) return null;

  const color = BRANCH_COLORS[selectedBranch];
  const icon = BRANCH_ICONS[selectedBranch];
  const branchData = comparison?.branches.find(b => b.branch === selectedBranch);

  function toast(msg: string) {
    setToastMsg(msg);
    setToastVisible(true);
    setTimeout(() => setToastVisible(false), 2000);
  }

  return (
    <MobileShell>
      <DdayBar dday={comparison?.dday} noticeDaysLeft={comparison?.noticeDaysLeft} />

      {/* 갈래 헤더 */}
      <div className="px-5 py-3 flex items-center gap-2" style={{ background: color + '22', borderBottom: `2px solid ${color}` }}>
        {/* 동네 선택에서 바로 오는 경로(SC-04/05)가 생겨 "항상 SC-07/SC-08에서 왔다"는 가정이 깨짐 —
            실제 직전 화면(prevScreen)으로 돌아가고, 못 잡을 때만 기존 가정으로 폴백 */}
        <BackBtn onClick={() => dispatch({ type: 'NAVIGATE', screen: prevScreen ?? (selectedBranch === '갱신' ? 'SC-08' : 'SC-07') })} />
        <span className="text-xl">{icon}</span>
        <h1 className="text-lg font-bold" style={{ color }}>
          {selectedBranch} · KB 금융 패키지
        </h1>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-5 space-y-4">
        {/* 상품 사유는 백엔드 LLM seam(상품별 1콜) — 응답 전 빈 화면 대신 스켈레톤으로 '불러오는 중' 신호 */}
        {!products ? <FinanceSkeleton color={color} /> : <>
        {/* Q1: 상품은 자격 기준 — 동네와 무관함을 명시(동네 카드엔 상품 미표시, 여기 한 곳) */}
        <p className="text-[11px] px-1" style={{ color: COLORS.SUB }}>
          아래 상품은 <b>당신 자격 기준</b>이에요(동네와 무관). 상품명을 누르면 공식 페이지로 이어져요.
        </p>

        {/* 메인 대출 카드 — "예상 월 부담"은 이 카드 내부 "예상 월 상환"과 같은 값이라 중복 표시하지 않음 */}
        <div
          className="bg-card rounded-3xl border-2 overflow-hidden"
          style={{ borderColor: color, boxShadow: '0 2px 12px rgba(0,0,0,0.08)' }}
        >
          <div className="px-5 pt-5 pb-3 flex items-start justify-between">
            <div className="flex-1">
              <span className="text-xs font-bold px-2 py-0.5 rounded-full text-white mb-2 inline-block" style={{ background: color }}>
                주요 대출
              </span>
              <ProductName name={products.mainLoan.name} className="text-base font-bold mt-1 inline-block" />
              <p className="text-sm text-muted-foreground mt-0.5">{products.mainLoan.condition}</p>
            </div>
          </div>

          {/* AI 브리핑 (추천 사유) */}
          <div className="mx-5 mb-4">
            <AiBriefing
              text={briefings.finance(selectedBranch, products.mainLoan.recommendReason)}
              compact
            />
          </div>

          {products.mainLoan.maxAmount && (
            <div className="mx-5 mb-4 grid grid-cols-2 gap-3">
              <div className="bg-muted rounded-xl px-3 py-2.5">
                <p className="text-xs text-muted-foreground">최대 한도</p>
                <p className="font-bold mt-0.5">{formatAmount(products.mainLoan.maxAmount)}</p>
              </div>
              {branchData && (
                <div className="bg-muted rounded-xl px-3 py-2.5">
                  <p className="text-xs text-muted-foreground">예상 월 상환</p>
                  <p className="font-bold mt-0.5">{formatAmount(branchData.monthlyBurden)}</p>
                </div>
              )}
            </div>
          )}

          <div className="px-5 pb-4 flex items-center gap-2">
            <BasisChip label={products.mainLoan.basis} tip={products.mainLoan.basis} />
          </div>
        </div>

        {/* 연결선 */}
        <div className="flex justify-center">
          <div className="w-px h-6 bg-border" />
        </div>

        {/* 보장 서브 카드 */}
        {products.guarantee && (
          <div className="bg-card rounded-2xl border border-border overflow-hidden" style={{ boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}>
            <div className="px-5 pt-4 pb-3">
              <span className="text-xs text-muted-foreground font-medium">보장</span>
              <ProductName name={products.guarantee.name} className="font-semibold mt-1 inline-block" />
              <p className="text-sm text-muted-foreground">{products.guarantee.condition}</p>
              <p className="text-sm mt-2 text-foreground/80">{products.guarantee.recommendReason}</p>
            </div>
            <div className="px-5 pb-4">
              <SecondaryBtn
                onClick={() => {
                  const url = officialProductUrl(products.guarantee!.name);
                  if (url) window.open(url, '_blank', 'noopener,noreferrer');
                  else toast('PoC — 상품 페이지 연결 예정');
                }}
                className="h-10 text-sm"
              >
                공식 페이지에서 자세히 →
              </SecondaryBtn>
            </div>
          </div>
        )}

        {/* 추가 상품 */}
        {products.extra && (
          <div className="bg-card rounded-2xl border border-border p-4">
            <div className="flex items-start justify-between">
              <div>
                <span className="text-xs text-muted-foreground">추가</span>
                <ProductName name={products.extra.name} className="font-semibold inline-block" />
                <p className="text-sm text-muted-foreground mt-0.5">{products.extra.condition}</p>
                <p className="text-sm mt-1">{products.extra.recommendReason}</p>
              </div>
            </div>
          </div>
        )}
        </>}
      </div>

      <div className="px-5 pb-8 pt-3 space-y-3">
        <PrimaryBtn onClick={() => products && dispatch({ type: 'NAVIGATE', screen: 'SC-10' })} disabled={!products}>
          상담 예약하기
        </PrimaryBtn>
        <button
          onClick={() => dispatch({ type: 'NAVIGATE', screen: 'SC-11' })}
          className="w-full text-sm text-muted-foreground underline py-2"
        >
          나중에 할게요, 저장만 할게요
        </button>
      </div>

      <Disclaimer />
      <Toast message={toastMsg} visible={toastVisible} />
    </MobileShell>
  );
}
