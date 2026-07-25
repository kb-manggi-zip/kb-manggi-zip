import React, { useEffect, useState, useRef } from 'react';
import { COLORS } from '../theme';

interface AiBriefingProps {
  text: string;
  compact?: boolean;
  live?: boolean;   // true면 외부(SSE)가 점진 공급하는 text를 그대로 렌더 (내부 타이핑 X)
  done?: boolean;   // live 모드에서 스트림 완료 여부 (커서 제거)
}

export default function AiBriefing({ text, compact = false, live = false, done: doneProp = false }: AiBriefingProps) {
  const [displayed, setDisplayed] = useState('');
  const [done, setDone] = useState(false);
  const idxRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (live) return;   // 외부 공급 모드 — 내부 타이핑 안 함
    idxRef.current = 0;
    setDisplayed('');
    setDone(false);

    function tick() {
      idxRef.current += 1;
      setDisplayed(text.slice(0, idxRef.current));
      if (idxRef.current < text.length) {
        timerRef.current = setTimeout(tick, 28);
      } else {
        setDone(true);
      }
    }
    timerRef.current = setTimeout(tick, 60);
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [text, live]);

  const shownText = live ? text : displayed;
  const shownDone = live ? doneProp : done;

  if (compact) {
    return (
      <div className="flex items-start gap-2 px-4 py-3 rounded-2xl bg-muted/60">
        <span
          className="flex-none w-6 h-6 rounded-full flex items-center justify-center text-xs font-black"
          style={{ background: COLORS.KB_YELLOW, color: COLORS.TEXT, fontSize: 9 }}
        >
          AI
        </span>
        <p className="text-sm text-foreground leading-relaxed flex-1">
          {shownText}
          {!shownDone && <span className="inline-block w-0.5 h-3.5 bg-foreground/50 ml-0.5 animate-pulse" />}
        </p>
      </div>
    );
  }

  return (
    <div className="mx-5 mb-4">
      <div className="flex items-start gap-3">
        {/* AI 아바타 */}
        <div className="flex-none flex flex-col items-center gap-1">
          <div
            className="w-9 h-9 rounded-full flex items-center justify-center font-black"
            style={{ background: COLORS.YELLOW_SURFACE, border: `2px solid ${COLORS.KB_YELLOW}`, fontSize: 10, color: COLORS.KB_GRAY }}
          >
            ✨
          </div>
          <span className="text-[9px] font-semibold text-muted-foreground">KB AI</span>
        </div>

        {/* 말풍선 */}
        <div
          className="flex-1 rounded-2xl rounded-tl-sm px-4 py-3 relative"
          style={{ background: COLORS.YELLOW_SURFACE, border: `1px solid ${COLORS.KB_YELLOW}44` }}
        >
          {/* 꼬리 */}
          <div
            className="absolute -left-1.5 top-3 w-3 h-3 rounded-sm"
            style={{ background: COLORS.YELLOW_SURFACE, border: `1px solid ${COLORS.KB_YELLOW}44`, borderRight: 'none', borderBottom: 'none', transform: 'rotate(-45deg)' }}
          />
          <p className="text-sm text-foreground leading-relaxed">
            {shownText}
            {!shownDone && <span className="inline-block w-0.5 h-3.5 bg-foreground/40 ml-0.5 animate-pulse" />}
          </p>
        </div>
      </div>
      <p className="text-[11px] text-muted-foreground mt-1.5 ml-12">
        ⓘ 입력하신 정보와 공개 기준으로 계산한 결과를 설명해드려요
      </p>
    </div>
  );
}
