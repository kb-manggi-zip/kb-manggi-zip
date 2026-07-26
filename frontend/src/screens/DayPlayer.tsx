import React, { useState, useEffect } from 'react';
import { useApp } from '../store';
import { COLORS, BRANCH_COLORS, BRANCH_ICONS } from '../theme';
import { MobileShell, BasisChip } from '../components/ui';
import { api, briefings } from '../api/client';
import { formatAmount } from '../utils/format';
import type { Scene } from '../api/types';

export default function DayPlayer() {
  const { state, dispatch } = useApp();
  const { selectedBranch, selectedRegionId, selectedRegion, finance, comparison } = state;
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [monthlyCost, setMonthlyCost] = useState(0);
  const [lifestyle, setLifestyle] = useState('');
  const [current, setCurrent] = useState(0);
  const [autoPlay, setAutoPlay] = useState(true);
  const [showIntro, setShowIntro] = useState(true);

  // 찾은 동네 이름(한글) — 선택 Region 우선, 없으면 id prefix 폴백
  const regionName = selectedRegion?.name
    ?? (selectedRegionId ? selectedRegionId.split('-')[0] : '이 동네');

  useEffect(() => {
    if (!selectedBranch || !selectedRegionId) return;
    api.simulate(selectedBranch, selectedRegionId).then(r => {
      setScenes(r.scenes);
      setMonthlyCost(r.monthlyCost);
    });
    // '이 동네에서의 하루' 개인화 발품 내레이션(소비 프로필 그라운딩)
    api.dayLifestyle(selectedRegion, selectedBranch, finance).then(setLifestyle);
    // 1초 전환 카드
    const t = setTimeout(() => setShowIntro(false), 1500);
    return () => clearTimeout(t);
  }, [selectedBranch, selectedRegionId]);

  useEffect(() => {
    if (!autoPlay || scenes.length === 0) return;
    const t = setTimeout(() => {
      if (current < scenes.length - 1) setCurrent(c => c + 1);
      else setAutoPlay(false);
    }, 4000);
    return () => clearTimeout(t);
  }, [current, autoPlay, scenes]);

  if (!selectedBranch) return null;

  const color = BRANCH_COLORS[selectedBranch];
  const icon = BRANCH_ICONS[selectedBranch];
  const scene = scenes[current];
  const isLast = current === scenes.length - 1;

  // 1초 인트로 카드
  if (showIntro) {
    return (
      <div
        className="flex flex-col items-center justify-center"
        style={{ width: '100%', maxWidth: 390, height: '100dvh', margin: '0 auto', background: '#111' }}
      >
        <div
          className="px-8 py-6 rounded-3xl text-center space-y-3"
          style={{ background: 'rgba(255,255,255,0.1)', backdropFilter: 'blur(12px)' }}
        >
          <p className="text-3xl">✨</p>
          <p className="text-white text-lg font-bold">
            {briefings.dayPlayer(regionName)}
          </p>
          <p className="text-white/50 text-sm">잠시 후 시작해요</p>
        </div>
      </div>
    );
  }

  if (scenes.length === 0) return null;

  function handleTap(e: React.MouseEvent<HTMLDivElement>) {
    const x = e.clientX;
    const mid = window.innerWidth / 2;
    if (x > mid) {
      if (current < scenes.length - 1) { setCurrent(c => c + 1); setAutoPlay(false); }
    } else {
      if (current > 0) { setCurrent(c => c - 1); setAutoPlay(false); }
    }
  }

  return (
    <div
      className="relative overflow-hidden"
      style={{ width: '100%', maxWidth: 390, height: '100dvh', margin: '0 auto', background: '#111' }}
      onClick={handleTap}
    >
      {/* 배경 이미지 */}
      <div
        className="absolute inset-0 bg-cover bg-center transition-all duration-700"
        style={{ backgroundImage: `url(${scene.visual})` }}
      >
        <div className="absolute inset-0 bg-gradient-to-b from-black/20 via-transparent to-black/70" />
      </div>

      {/* 상단 */}
      <div className="absolute top-0 left-0 right-0 z-20 p-5 space-y-3">
        {/* 프로그레스 도트 */}
        <div className="flex gap-1">
          {scenes.map((_, i) => (
            <div
              key={i}
              className="flex-1 h-0.5 rounded-full transition-all duration-300"
              style={{ background: i <= current ? '#fff' : 'rgba(255,255,255,0.3)' }}
            />
          ))}
        </div>

        {/* 갈래 칩 */}
        <div className="flex items-center gap-2">
          <button
            onClick={e => { e.stopPropagation(); dispatch({ type: 'NAVIGATE', screen: 'SC-04' }); }}
            className="text-white text-sm opacity-70 pr-2"
          >
            ←
          </button>
          <span
            className="inline-flex items-center gap-1 text-xs font-semibold px-3 py-1 rounded-full"
            style={{ background: color, color: '#fff' }}
          >
            {icon} {selectedBranch}
          </span>
        </div>
      </div>

      {/* 시간 스티커 */}
      <div
        className="absolute top-28 left-5 z-20 px-3 py-1.5 rounded-xl text-sm font-bold text-white"
        style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)' }}
      >
        {scene.time}
      </div>

      {/* 하단 자막 */}
      <div className="absolute bottom-0 left-0 right-0 z-20 p-6 space-y-2">
        {!isLast ? (
          <>
            <p className="text-white text-lg font-bold leading-snug drop-shadow">{scene.caption1}</p>
            <p className="text-white/80 text-sm">{scene.caption2}</p>
            {scene.basis && (
              <div onClick={e => e.stopPropagation()}>
                <BasisChip label="데이터" tip={scene.basis} />
              </div>
            )}
            <p className="text-white/40 text-xs pt-1">좌측 탭: 이전 · 우측 탭: 다음</p>
          </>
        ) : (
          <div className="space-y-4" onClick={e => e.stopPropagation()}>
            {lifestyle && (
              <div className="bg-black/60 rounded-2xl p-4" style={{ backdropFilter: 'blur(8px)' }}>
                <p className="text-white/70 text-xs mb-1">💬 이 동네에서의 당신</p>
                <p className="text-white text-sm leading-relaxed">{lifestyle}</p>
              </div>
            )}
            <div className="bg-black/60 rounded-2xl p-4" style={{ backdropFilter: 'blur(8px)' }}>
              <p className="text-white/70 text-xs mb-1">이 하루의 월 부담</p>
              <p className="text-white text-2xl font-bold">{formatAmount(monthlyCost)}/월</p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => dispatch({ type: 'NAVIGATE', screen: 'SC-03' })}
                className="py-3 rounded-full text-sm font-semibold border border-white/50 text-white"
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
        )}
      </div>
    </div>
  );
}
