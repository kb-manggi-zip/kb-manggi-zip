import React, { useState, useEffect } from 'react';
import { useApp } from '../store';
import { COLORS } from '../theme';
import { MobileShell } from '../components/ui';
import { SAVED_MONEY_CARDS, briefings } from '../api/client';
import { formatAmount } from '../utils/format';

export default function SavedMoneyPlayer() {
  const { state, dispatch } = useApp();
  const { comparison } = state;
  const [current, setCurrent] = useState(0);
  const [autoPlay, setAutoPlay] = useState(true);
  const [showIntro, setShowIntro] = useState(true);

  useEffect(() => {
    const t = setTimeout(() => setShowIntro(false), 1500);
    return () => clearTimeout(t);
  }, []);

  const savings = comparison?.savings || 0;

  const cards = SAVED_MONEY_CARDS.map((c, i) =>
    i === 0 ? { ...c, body: `이사 안 하면 일회성 비용 약 ${formatAmount(savings)}을 아껴요 — 이사비·중개비 부담 없이 지금 집에서 2년 더.` }
    : c
  );

  useEffect(() => {
    if (!autoPlay) return;
    const t = setTimeout(() => {
      if (current < cards.length - 1) setCurrent(c => c + 1);
      else setAutoPlay(false);
    }, 4000);
    return () => clearTimeout(t);
  }, [current, autoPlay]);

  function tap(e: React.MouseEvent<HTMLDivElement>) {
    const x = e.clientX;
    const mid = window.innerWidth / 2;
    if (x > mid && current < cards.length - 1) { setCurrent(c => c + 1); setAutoPlay(false); }
    else if (x <= mid && current > 0) { setCurrent(c => c - 1); setAutoPlay(false); }
  }

  const card = cards[current];
  const isLast = current === cards.length - 1;

  if (showIntro) {
    return (
      <MobileShell>
        <div
          className="flex-1 flex flex-col items-center justify-center bg-foreground"
        >
          <div
            className="px-8 py-6 rounded-3xl text-center space-y-3"
            style={{ background: 'rgba(255,255,255,0.1)', backdropFilter: 'blur(12px)' }}
          >
            <p className="text-3xl">✨</p>
            <p className="text-white text-lg font-bold">{briefings.savedMoney()}</p>
            <p className="text-white/50 text-sm">잠시 후 시작해요</p>
          </div>
        </div>
      </MobileShell>
    );
  }

  return (
    <MobileShell>
      <div
        className="flex-1 flex flex-col bg-foreground cursor-pointer"
        onClick={tap}
        style={{ userSelect: 'none' }}
      >
        {/* 프로그레스 */}
        <div className="flex gap-1 px-5 pt-6 pb-4">
          {cards.map((_, i) => (
            <div
              key={i}
              className="flex-1 h-0.5 rounded-full transition-all duration-300"
              style={{ background: i <= current ? COLORS.KB_YELLOW : 'rgba(255,255,255,0.2)' }}
            />
          ))}
        </div>

        {/* 갈래 칩 */}
        <div className="px-5 pb-6 flex items-center gap-2">
          <button
            onClick={e => { e.stopPropagation(); dispatch({ type: 'NAVIGATE', screen: 'SC-06' }); }}
            className="text-white/60 text-sm pr-2"
          >
            ←
          </button>
          <span
            className="inline-flex items-center gap-1 text-xs font-semibold px-3 py-1 rounded-full"
            style={{ background: COLORS.MINT, color: '#fff' }}
          >
            🏠 눌러앉기 · 갱신
          </span>
        </div>

        {/* 카드 콘텐츠 */}
        <div className="flex-1 flex flex-col justify-center px-8 space-y-6">
          <div
            className="text-6xl text-center"
            style={{ filter: 'drop-shadow(0 4px 16px rgba(0,0,0,0.3))' }}
          >
            {card.icon}
          </div>
          <div className="space-y-3 text-center">
            <h2 className="text-xl font-bold text-white leading-snug">{card.title}</h2>
            <p className="text-white/70 text-sm leading-relaxed">{card.body}</p>
            {card.sub && (
              <span className="inline-block text-xs px-3 py-1 rounded-full bg-white/10 text-white/50">
                {card.sub}
              </span>
            )}
          </div>
        </div>

        {/* 하단 */}
        {isLast ? (
          <div className="px-6 pb-10 space-y-3" onClick={e => e.stopPropagation()}>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => dispatch({ type: 'NAVIGATE', screen: 'SC-03' })}
                className="py-3 rounded-full text-sm font-semibold border border-white/30 text-white"
              >
                세 갈래 다시 보기
              </button>
              <button
                onClick={() => dispatch({ type: 'NAVIGATE', screen: 'SC-09' })}
                className="py-3 rounded-full text-sm font-semibold text-foreground"
                style={{ background: COLORS.KB_YELLOW }}
              >
                금융 알아보기
              </button>
            </div>
          </div>
        ) : (
          <p className="text-center text-white/30 text-xs pb-8">
            좌측 탭: 이전 · 우측 탭: 다음
          </p>
        )}
      </div>
    </MobileShell>
  );
}
