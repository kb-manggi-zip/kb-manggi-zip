import React, { useState, useEffect, useRef } from 'react';
import { useApp } from '../store';
import { COLORS } from '../theme';
import { MobileShell, DdayBar, BackBtn, PrimaryBtn, BasisChip, Disclaimer, Toast } from '../components/ui';
import AiBriefing from '../components/AiBriefing';
import { formatDate, formatAmount, noticeText } from '../utils/format';
import { briefings, api } from '../api/client';

interface CheckItem {
  id: string;
  title: string;
  desc: string;
  urgent?: boolean;
  tip?: string;
  tipLabel?: string;
  done: boolean;
}

// ─── 통보 문자 초안 바텀시트 ──────────────────────────────────────────────
function DraftSheet({ expiryDate, onClose }: { expiryDate: string; onClose: () => void }) {
  const [draft, setDraft] = useState('');
  const [typing, setTyping] = useState(true);
  const [toast, setToast] = useState<string | null>(null);
  const idxRef = useRef(0);

  useEffect(() => {
    api.draftNotice({ expiryDate }).then(res => {
      const full = res.draft;
      idxRef.current = 0;
      setDraft('');
      function tick() {
        idxRef.current += 1;
        setDraft(full.slice(0, idxRef.current));
        if (idxRef.current < full.length) setTimeout(tick, 18);
        else setTyping(false);
      }
      setTimeout(tick, 100);
    });
  }, [expiryDate]);

  function copyToClipboard() {
    navigator.clipboard.writeText(draft).then(() => {
      setToast('복사했어요. 문자앱에 붙여넣어 보내세요 ✓');
      setTimeout(() => setToast(null), 2500);
    });
  }

  return (
    <div
      className="fixed inset-0 z-50 flex flex-col justify-end"
      style={{ background: 'rgba(0,0,0,0.5)' }}
      onClick={e => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-card rounded-t-3xl overflow-hidden" style={{ maxHeight: '80dvh' }}>
        <div className="flex flex-col items-center pt-4 pb-2 px-5 border-b border-border">
          <div className="w-10 h-1 bg-border rounded-full mb-4" />
          {/* AI 헤더 */}
          <div className="flex items-center gap-2 mb-1">
            <span className="text-lg">✨</span>
            <p className="text-sm font-semibold text-foreground">
              집주인께 보낼 문자 초안을 만들었어요.
            </p>
          </div>
          <p className="text-xs text-muted-foreground text-center">
            확인하고 수정해서 보내세요.
          </p>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4" style={{ maxHeight: '55dvh' }}>
          {/* 편집 가능한 textarea */}
          <div
            className="rounded-2xl border-2 p-4"
            style={{ borderColor: COLORS.KB_YELLOW, background: COLORS.YELLOW_SURFACE }}
          >
            <textarea
              value={draft}
              onChange={e => setDraft(e.target.value)}
              rows={8}
              className="w-full bg-transparent text-sm text-foreground leading-relaxed outline-none resize-none"
              style={{ fontFamily: 'inherit' }}
            />
            {typing && (
              <span className="inline-block w-0.5 h-3.5 bg-foreground/50 animate-pulse" />
            )}
          </div>

          {/* [동·호수] 안내 */}
          <p className="text-xs text-muted-foreground">
            💡 <strong>[동·호수]</strong>는 직접 채워주세요. 만기일은 계약 정보에서 자동으로 가져왔어요.
          </p>

          <button
            onClick={copyToClipboard}
            disabled={typing}
            className="w-full h-12 rounded-full font-semibold text-sm transition-all active:scale-95"
            style={{ background: COLORS.KB_YELLOW, color: COLORS.TEXT, opacity: typing ? 0.5 : 1 }}
          >
            복사하기
          </button>

          <p className="text-xs text-muted-foreground text-center leading-relaxed pb-4">
            AI가 만든 초안이에요. 내용을 꼭 확인하고 보내세요.<br />
            법적 효력·기한은 계약서를 기준으로 하세요.
          </p>
        </div>
      </div>
      <Toast message={toast || ''} visible={toast !== null} />
    </div>
  );
}

// ─── 메인 화면 ────────────────────────────────────────────────────────────
export default function RenewalChecklist() {
  const { state, dispatch } = useApp();
  const { contract, comparison } = state;

  // 이 화면은 비교표 계산 이후에만 오므로 comparison의 단일 계산 결과를 그대로 씀 — 재계산 안 함.
  const noticeDeadline = comparison ? new Date(comparison.noticeDeadline) : new Date();
  const noticeDaysLeft = comparison?.noticeDaysLeft ?? 0;
  const isUrgent = noticeDaysLeft <= 14;
  const guaranteeMonthly = comparison?.branches.find(b => b.branch === '갱신')?.guaranteeMonthly || 0;
  const noticeDeadlineStr = formatDate(noticeDeadline);
  const briefText = briefings.renewal(noticeDeadlineStr);

  const [items, setItems] = useState<CheckItem[]>([
    {
      id: 'notice',
      title: '갱신 의사 통보',
      desc: `만기 2개월 전(${noticeDeadlineStr})까지 서면으로 통보해야 해요`,
      urgent: isUrgent,
      done: false,
    },
    {
      id: 'rate',
      title: '인상률 확인',
      desc: '법정 상한 5% 이내인지 확인하세요',
      tip: '「주택임대차보호법」 제7조 — 증액은 직전 임대료의 5% 이내',
      tipLabel: '법정 근거',
      done: false,
    },
    {
      id: 'guarantee',
      title: '반환보증 가입/갱신 점검',
      desc: `갱신 계약 후 보증 재가입 확인 · 보증료 월 환산 약 ${Math.round(guaranteeMonthly / 10_000)}만원`,
      tip: '보증기관 공시 요율 기준 추정치예요',
      tipLabel: '보증료 산출',
      done: false,
    },
    {
      id: 'clause',
      title: '계약서 특약 확인',
      desc: '수선의무·관리비 항목·중도해지 조항 등을 점검해요',
      done: false,
    },
  ]);

  const [draftOpen, setDraftOpen] = useState(false);
  const allDone = items.every(i => i.done);

  function toggle(id: string) {
    setItems(items.map(i => i.id === id ? { ...i, done: !i.done } : i));
  }

  return (
    <MobileShell>
      <DdayBar dday={comparison?.dday} noticeDaysLeft={comparison?.noticeDaysLeft} />

      <div className="flex items-center gap-2 px-5 py-3 border-b-2" style={{ borderColor: COLORS.MINT }}>
        <BackBtn onClick={() => dispatch({ type: 'NAVIGATE', screen: 'SC-03' })} />
        <span className="text-lg">🏠</span>
        <span className="font-bold" style={{ color: COLORS.MINT }}>갱신 절차</span>
      </div>

      <div className="flex-1 overflow-y-auto">
        {/* AI 브리핑 */}
        <div className="pt-4">
          <AiBriefing text={briefText} />
        </div>

        <div className="px-5 pb-2 space-y-1">
          <h1 className="text-xl font-bold" style={{ color: COLORS.KB_GRAY }}>갱신 체크리스트</h1>
          <p className="text-sm text-muted-foreground">항목을 확인하며 체크해보세요</p>
        </div>

        <div className="px-5 py-3 space-y-3">
          {items.map((item, idx) => (
            <div key={item.id}>
              <button
                onClick={() => toggle(item.id)}
                className="w-full text-left bg-card rounded-2xl border-2 p-4 transition-all active:scale-[0.98]"
                style={{
                  borderColor: item.done ? COLORS.MINT : item.urgent ? COLORS.CORAL : COLORS.BORDER,
                  boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
                }}
              >
                <div className="flex items-start gap-3">
                  <div
                    className="w-7 h-7 rounded-full flex-none flex items-center justify-center text-sm font-bold border-2 transition-all mt-0.5"
                    style={{
                      background: item.done ? COLORS.MINT : 'transparent',
                      borderColor: item.done ? COLORS.MINT : item.urgent ? COLORS.CORAL : COLORS.BORDER,
                      color: item.done ? '#fff' : COLORS.KB_GRAY,
                    }}
                  >
                    {item.done ? '✓' : idx + 1}
                  </div>
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="font-semibold text-foreground">{item.title}</p>
                      {item.urgent && (
                        <span
                          className="text-xs font-bold px-2 py-0.5 rounded-full text-white"
                          style={{ background: COLORS.CORAL }}
                        >
                          ⚠️ {noticeText(noticeDaysLeft)}
                        </span>
                      )}
                      {item.tip && <BasisChip label={item.tipLabel || '근거'} tip={item.tip} />}
                    </div>
                    <p className="text-sm text-muted-foreground">{item.desc}</p>
                  </div>
                </div>
              </button>

              {/* ① 통보 항목에만: 문자 초안 버튼 */}
              {item.id === 'notice' && (
                <button
                  onClick={() => setDraftOpen(true)}
                  className="mt-2 ml-10 flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-full border transition-colors"
                  style={{ borderColor: COLORS.MINT, color: COLORS.MINT, background: COLORS.MINT + '15' }}
                >
                  📝 통보 문자 초안 받기
                </button>
              )}
            </div>
          ))}

          {allDone && (
            <div className="px-4 py-4 rounded-2xl text-center space-y-2" style={{ background: COLORS.MINT + '22' }}>
              <p className="text-lg">🎉</p>
              <p className="font-semibold" style={{ color: COLORS.MINT }}>모두 확인했어요!</p>
            </div>
          )}
        </div>
      </div>

      <div className="px-5 pb-8 pt-3">
        <PrimaryBtn onClick={() => dispatch({ type: 'NAVIGATE', screen: 'SC-08' })}>
          갱신하며 아끼는 돈 보기 →
        </PrimaryBtn>
      </div>

      <Disclaimer />

      {/* 문자 초안 바텀시트 */}
      {draftOpen && contract && (
        <DraftSheet expiryDate={contract.expiryDate} onClose={() => setDraftOpen(false)} />
      )}
    </MobileShell>
  );
}
