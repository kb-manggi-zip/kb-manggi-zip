import React, { useState, useEffect } from 'react';
import { useApp } from '../store';
import { COLORS, BRANCH_COLORS, BRANCH_ICONS } from '../theme';
import { MobileShell, BasisChip } from '../components/ui';
import { KakaoMap } from '../components/KakaoMap';
import { api, briefings } from '../api/client';
import { formatAmount, ddayText } from '../utils/format';
import { deriveLeadSignal } from '../utils/leadSignal';
import type { Scene } from '../api/types';

// 시간대 그라디언트 — 스톡사진 대신 시간의 '색'으로 하루를 표현(아침 웜/낮 스카이/저녁 앰버/밤 네이비).
function timeGradient(time: string): string {
  const h = parseInt((time.match(/(\d{1,2}):/) || [])[1] || '12', 10);
  if (h >= 5 && h < 10) return 'linear-gradient(160deg, #FFD9A0 0%, #FFB86C 55%, #E8925A 100%)';   // 아침
  if (h >= 10 && h < 16) return 'linear-gradient(160deg, #CDEBFF 0%, #9FD0F5 55%, #6FB0E8 100%)';  // 낮
  if (h >= 16 && h < 19) return 'linear-gradient(160deg, #FFC98A 0%, #FF9E5E 55%, #D9663C 100%)';  // 저녁
  return 'linear-gradient(160deg, #3A3F6B 0%, #23264A 55%, #14162E 100%)';                          // 밤
}

// 요약 화면 배경 — 마지막 씬(예: 저녁 18:30)의 시간대색을 그대로 이어받으면 "아직 그 장면"처럼 보여
// 혼동을 줌. 하루를 다 보여준 뒤의 별도 마무리 화면임을 표시하는 중립 다크 톤 고정.
const SUMMARY_GRADIENT = 'linear-gradient(160deg, #3A3F6B 0%, #23264A 55%, #14162E 100%)';

export default function DayPlayer() {
  const { state, dispatch } = useApp();
  const { selectedBranch, selectedRegionId, selectedRegion, finance, comparison } = state;
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [monthlyCost, setMonthlyCost] = useState(0);
  const [lifestyle, setLifestyle] = useState('');
  const [current, setCurrent] = useState(0);
  const [autoPlay, setAutoPlay] = useState(true);
  const [showIntro, setShowIntro] = useState(true);
  // 고정 3씬은 다 온전히 보여주고, 지도·요약(마무리 화면)은 그 뒤에 별도로 — 마지막 씬 캡션이
  // 요약 블록에 가려서 안 보이던 문제 수정(2026-08-02).
  const [showSummary, setShowSummary] = useState(false);

  // 찾은 동네 이름(한글) — 선택 Region 우선, 없으면 id prefix 폴백
  const regionName = selectedRegion?.name
    ?? (selectedRegionId ? selectedRegionId.split('-')[0] : '이 동네');

  useEffect(() => {
    if (!selectedBranch || !selectedRegionId) return;
    const branchBudget = comparison?.branches.find(b => b.branch === selectedBranch)?.depositOrPrice;
    // 하루시뮬 고정 3씬(통근+상권태그 우선순위)은 소비신호로 정해짐 — RegionList의 leadSignal과 같은 파생.
    // 실패해도 백엔드가 신호 없이(폴백 순서로) 정상 조립하므로 시뮬 자체는 막지 않는다.
    const leadSignalPromise = state.contract && finance
      ? api.persona(state.contract, finance, branchBudget).then(p => deriveLeadSignal(p.consumptionSignals)).catch(() => undefined)
      : Promise.resolve(undefined);
    leadSignalPromise.then(leadSignal => {
      api.simulate(selectedBranch, selectedRegionId, finance?.household, leadSignal).then(r => {
        setScenes(r.scenes);
        setMonthlyCost(r.monthlyCost);
      });
    });
    // '이 동네에서의 하루' 개인화 발품 내레이션(소비 프로필 그라운딩)
    // budget = 고른 갈래 예산 → 발품 실거래를 예산 이하에서 선정(G2)
    // wfh = 통근 비중을 낮추기로 확정(재택 등)한 사용자 → 발품에서 통근 격하(G3)
    const wfh = (state.contract?.noteAdjust?.commute ?? 1) < 0.95;
    api.dayLifestyle(selectedRegion, selectedBranch, finance, branchBudget, wfh).then(setLifestyle);
    // 1초 전환 카드
    const t = setTimeout(() => setShowIntro(false), 1500);
    return () => clearTimeout(t);
  }, [selectedBranch, selectedRegionId]);

  useEffect(() => {
    if (!autoPlay || showSummary || scenes.length === 0) return;
    const t = setTimeout(() => {
      if (current < scenes.length - 1) setCurrent(c => c + 1);
      else { setShowSummary(true); setAutoPlay(false); }
    }, 4000);
    return () => clearTimeout(t);
  }, [current, autoPlay, showSummary, scenes]);

  if (!selectedBranch) return null;

  const color = BRANCH_COLORS[selectedBranch];
  const icon = BRANCH_ICONS[selectedBranch];
  const scene = scenes[current];
  // 진행 도트: 고정 3씬 + 요약을 4번째 스텝으로 시각화(요약도 별도 "화면"임을 보여줌).
  const activeIndex = showSummary ? scenes.length : current;
  // §4.3: 마지막 씬 월 부담 = 비교표(compare)의 선택 갈래 값(일관). 씬 fixture(monthlyCost)와의 불일치 해소.
  const selectedBurden = comparison?.branches.find(b => b.branch === selectedBranch)?.monthlyBurden;

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
    setAutoPlay(false);
    if (x > mid) {
      if (showSummary) return; // 요약 화면에선 우측 탭 없음(CTA 버튼으로 진행)
      if (current < scenes.length - 1) setCurrent(c => c + 1);
      else setShowSummary(true);
    } else {
      if (showSummary) setShowSummary(false);
      else if (current > 0) setCurrent(c => c - 1);
    }
  }

  return (
    <div
      className="relative overflow-hidden"
      style={{ width: '100%', maxWidth: 390, height: '100dvh', margin: '0 auto', background: '#111' }}
      onClick={handleTap}
    >
      {/* 배경 — 시간대 그라디언트(스톡사진 제거) + 하단 어둡게(자막 가독). 요약 화면은 중립 톤 고정. */}
      <div className="absolute inset-0 transition-all duration-700" style={{ background: showSummary ? SUMMARY_GRADIENT : timeGradient(scene.time) }}>
        <div className="absolute inset-0 bg-gradient-to-b from-black/15 via-transparent to-black/75" />
      </div>

      {/* 상단 */}
      <div className="absolute top-0 left-0 right-0 z-20 p-5 space-y-3">
        {/* 프로그레스 도트 */}
        <div className="flex gap-1">
          {[...scenes, null].map((_, i) => (
            <div
              key={i}
              className="flex-1 h-0.5 rounded-full transition-all duration-300"
              style={{ background: i <= activeIndex ? '#fff' : 'rgba(255,255,255,0.3)' }}
            />
          ))}
        </div>

        {/* 갈래 칩 */}
        <div className="flex items-center gap-2">
          <button
            onClick={e => { e.stopPropagation(); dispatch({ type: 'BACK', fallback: 'SC-04' }); }}
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
          {comparison && (
            <span
              className="ml-auto inline-flex items-center text-xs font-semibold px-3 py-1 rounded-full"
              style={{ background: 'rgba(0,0,0,0.35)', color: '#fff' }}
            >
              만기 {ddayText(comparison.dday)}
            </span>
          )}
        </div>
      </div>

      {/* 시간 스티커 — 요약 화면은 특정 시각이 아니므로 숨김 */}
      {!showSummary && (
        <div
          className="absolute top-28 left-5 z-20 px-3 py-1.5 rounded-xl text-sm font-bold text-white"
          style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)' }}
        >
          {scene.time}
        </div>
      )}

      {/* 하단 자막 */}
      <div className="absolute bottom-0 left-0 right-0 z-20 p-6 space-y-2">
        {!showSummary ? (
          <>
            <p className="text-white text-2xl font-bold leading-tight drop-shadow">{scene.caption1}</p>
            <p className="text-white/80 text-sm">{scene.caption2}</p>
            {scene.basis && (
              <div onClick={e => e.stopPropagation()}>
                {/* 장면 카드는 연출 예시 — 실측 수치는 하단 발품 내레이션·fact 칩이 담당(L1) */}
                <BasisChip label="장면" tip={scene.basis} />
              </div>
            )}
            <p className="text-white/40 text-xs pt-1">좌측 탭: 이전 · 우측 탭: 다음</p>
          </>
        ) : (
          <div className="space-y-3" onClick={e => e.stopPropagation()}>
            {/* 그 동네 좌표 — 실제 카카오맵(단일 핀). 키 없거나 로드 실패 시 KakaoMap이 조용히 placeholder로 대체 */}
            {selectedRegion?.lat ? (
              <KakaoMap
                pins={[{ id: selectedRegionId ?? regionName, name: regionName, lat: selectedRegion.lat, lng: selectedRegion.lng }]}
                height={84}
                className="rounded-2xl overflow-hidden"
              />
            ) : null}
            {lifestyle && (
              <div className="bg-black/60 rounded-2xl p-4" style={{ backdropFilter: 'blur(8px)' }}>
                <p className="text-white/70 text-xs mb-1">💬 이 동네에서의 당신</p>
                <p className="text-white text-sm leading-relaxed">{lifestyle}</p>
                {/* 소비 계보 — narrator에 실제 주입되는 건 '연령대 세그먼트 소비 성향'(카드소비 근사). 실측/진술 아님 */}
                <p className="text-white/40 text-[11px] mt-2 pt-2 border-t border-white/10">
                  이 하루의 톤: 연령대 세그먼트 소비 성향 + 동네 실데이터(통근·상권·실거래) 반영
                </p>
              </div>
            )}
            <div className="bg-black/60 rounded-2xl p-4" style={{ backdropFilter: 'blur(8px)' }}>
              <p className="text-white/70 text-xs mb-1">선택하신 {selectedBranch}의 월 부담 (비교표와 동일)</p>
              <p className="text-white text-2xl font-bold">{formatAmount(selectedBurden ?? monthlyCost)}/월</p>
              <p className="text-white/50 text-[11px] mt-1">규제·금리 기준 계산값 · {regionName} 시세로 산출</p>
            </div>
            {/* 지출 여력으로 연결 */}
            <button
              onClick={() => dispatch({ type: 'NAVIGATE', screen: 'SC-13' })}
              className="w-full py-3 rounded-full text-sm font-bold text-foreground"
              style={{ background: COLORS.KB_YELLOW }}
            >
              이 하루, 실현 가능한지 볼까요? →
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
