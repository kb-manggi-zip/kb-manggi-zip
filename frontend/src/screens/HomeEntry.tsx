import React, { useState } from "react";
import { useApp } from "../store";
import { COLORS, BRANCH_ICONS } from "../theme";
import { MobileShell, PrimaryBtn, Toast } from "../components/ui";
import {
  formatDday,
  formatDate,
  formatNoticeDeadline,
  formatAmount,
  ddayText,
  daysUntil,
} from "../utils/format";
import { NOTICE_DEADLINE_MONTHS, PERSONAS, api } from "../api/client";

const TAB_TOAST_MSG = "이 데모에서는 '추천' 탭의 만기 도우미를 소개해요 🙂";
// 골든패스 프리셋 노출 여부 — 기본 노출(데모 빌드가 곧 배포본). VITE_HIDE_DEMO=1이면 숨김.
const SHOW_DEMO_PRESETS = import.meta.env.VITE_HIDE_DEMO !== "1";
const TABS = ["추천", "매물", "시세", "청약", "뉴스"];

export default function HomeEntry() {
  const { state, dispatch } = useApp();
  const { contract, comparison } = state;
  const [toast, setToast] = useState<string | null>(null);

  // comparison(단일 계산 결과)이 있으면 그걸 그대로 쓰고, 계산 전(프리셋만 채운 직후 등)엔 로컬로 추정.
  const dday =
    comparison?.dday ?? (contract ? formatDday(contract.expiryDate) : null);
  const noticeDeadline = comparison
    ? new Date(comparison.noticeDeadline)
    : contract
    ? formatNoticeDeadline(contract.expiryDate, NOTICE_DEADLINE_MONTHS)
    : null;
  const noticeDaysLeft =
    comparison?.noticeDaysLeft ??
    (noticeDeadline ? daysUntil(noticeDeadline) : null);
  const hasData = contract !== null;

  function showToast(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(null), 2500);
  }

  // 골든패스 프리셋: 입력값(contract/finance)을 채우고, SC-12와 동일한 실제 계산 API를 그 자리에서
  // 호출해 comparison까지 바로 채운다 — 계산 우회 없이 결과만 화면 이동 없이 미리 보여줌.
  // SET_CONTRACT가 계약을 통째 교체하므로 이전 note/noteAdjust도 초기화됨.
  function loadPreset(p: (typeof PERSONAS)[number]) {
    dispatch({ type: "SET_CONTRACT", contract: p.contract });
    dispatch({ type: "SET_FINANCE", finance: p.finance });
    showToast(`${p.id} ${p.label} 데모 입력을 채웠어요 ✓`);
    api.analyze({ contract: p.contract, finance: p.finance }).then((result) => {
      dispatch({
        type: "SET_COMPARISON",
        comparison: result.comparison,
        briefing: result.briefing,
      });
    });
  }

  return (
    <MobileShell>
      {/* KB부동산 앱 헤더 */}
      <header className="flex items-center gap-3 px-5 pt-5 pb-3">
        <div
          className="w-10 h-10 rounded-xl flex items-center justify-center text-foreground font-black text-sm"
          style={{ background: COLORS.KB_YELLOW }}
        >
          KB
        </div>
        <span className="text-lg font-bold" style={{ color: COLORS.KB_GRAY }}>
          KB부동산
        </span>
        <div className="ml-auto flex gap-3 text-xl text-muted-foreground">
          <button>🔍</button>
          <button>🔔</button>
        </div>
      </header>

      {/* 탭바 — 추천 외 탭 탭 시 토스트 */}
      <div className="flex border-b border-border px-5 text-sm">
        {TABS.map((tab, i) => (
          <button
            key={tab}
            onClick={() => i !== 0 && showToast(TAB_TOAST_MSG)}
            className="flex-1 py-2.5 font-medium transition-colors"
            style={{
              color: i === 0 ? COLORS.KB_YELLOW : COLORS.SUB,
              borderBottom:
                i === 0
                  ? `2px solid ${COLORS.KB_YELLOW}`
                  : "2px solid transparent",
              marginBottom: -1,
            }}
          >
            {tab}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-5 space-y-4">
        {/* 만기 결정 도우미 위젯 */}
        <div
          className="rounded-3xl border border-border bg-card p-5 space-y-4 relative"
          style={{ boxShadow: "0 2px 12px rgba(0,0,0,0.07)" }}
        >
          <div>
            {dday !== null ? (
              <>
                <p className="text-xs text-muted-foreground mb-1">
                  계약 만기까지
                </p>
                <div className="flex items-baseline gap-2">
                  <span
                    className="font-black text-5xl leading-none"
                    style={{ color: COLORS.KB_GRAY }}
                  >
                    {ddayText(dday)}
                  </span>
                  <span className="text-sm text-muted-foreground">
                    {formatDate(new Date(contract!.expiryDate))}
                  </span>
                </div>
              </>
            ) : (
              <>
                <p className="text-xs text-muted-foreground mb-1">
                  전월세 만기 결정 도우미
                </p>
                <p
                  className="text-xl font-bold"
                  style={{ color: COLORS.KB_GRAY }}
                >
                  갱신할까, 이사할까, 매매할까?
                </p>
                {/* 갈래 미니 라벨 */}
                <div className="flex gap-3 mt-2">
                  {(["갱신", "이사", "매매"] as const).map((b) => (
                    <span
                      key={b}
                      className="text-xs text-muted-foreground flex items-center gap-1"
                    >
                      {BRANCH_ICONS[b]} {b}
                    </span>
                  ))}
                </div>
              </>
            )}
          </div>

          {/* 갱신 의사 통보기한 진행바 — 이 바는 오직 통보기한 하나만 기준(만기는 위에 별도 표시). */}
          {contract && noticeDeadline && noticeDaysLeft !== null && (
            <div className="space-y-2">
              <div className="relative h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className="absolute left-0 h-full rounded-full"
                  style={{
                    width: `${Math.max(
                      0,
                      Math.min(100, (1 - noticeDaysLeft / 120) * 100)
                    )}%`,
                    background: COLORS.CORAL,
                    transition: "width 0.5s",
                  }}
                />
              </div>
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>오늘</span>
                <span className="text-center" style={{ color: COLORS.CORAL }}>
                  갱신 의사 통보기한 <br />
                  {noticeDaysLeft < 0 ? "지남" : `D-${noticeDaysLeft} · ${formatDate(noticeDeadline)}`}
                </span>
              </div>
            </div>
          )}

          {/* 비교표 미니 요약 */}
          {comparison && (
            <div className="space-y-3">
              <div className="grid grid-cols-3 gap-2">
                {comparison.branches.map((b) => (
                  <div
                    key={b.branch}
                    className="bg-muted rounded-xl p-2 text-center"
                  >
                    <p className="text-xs text-muted-foreground">
                      {BRANCH_ICONS[b.branch]} {b.branch}
                    </p>
                    <p className="text-sm font-bold">
                      {formatAmount(b.monthlyBurden)}/월
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          <PrimaryBtn
            className="!h-11 text-sm"
            onClick={() =>
              dispatch({
                type: "NAVIGATE",
                screen: hasData ? "SC-03" : "SC-02",
              })
            }
          >
            {hasData ? "비교표 다시 보기 →" : "미리 계산해보기 →"}
          </PrimaryBtn>
          <div className="rounded-xl bg-muted px-3 py-2.5 text-center">
            <p className="text-xs text-muted-foreground">
              지금 결정하지 않아도 괜찮아요 ☁️
              <br />
              미리 계산만 해두고, 나중에 골라도 돼요.
            </p>
          </div>
          {hasData && (
            <button
              onClick={() => {
                dispatch({ type: "RESET" });
                dispatch({ type: "NAVIGATE", screen: "SC-02" });
              }}
              className="block w-full text-center text-xs text-muted-foreground underline"
            >
              🔄 새로 계산하기 (이전 입력 지우기)
            </button>
          )}
        </div>

        {/* 관심 지역 매물 (더미) */}
        <div>
          <p className="text-sm font-semibold text-muted-foreground mb-3">
            내 관심 지역 매물
          </p>
          <div className="space-y-3">
            {[
              {
                area: "마포구 합정동",
                type: "아파트",
                size: "84㎡",
                price: "5.3억",
                change: "+1.2%",
              },
              {
                area: "성북구 길음동",
                type: "빌라",
                size: "59㎡",
                price: "2.9억",
                change: "+0.8%",
              },
            ].map((item) => (
              <div
                key={item.area}
                className="flex items-center justify-between bg-card rounded-2xl px-4 py-3 border border-border"
              >
                <div>
                  <p className="text-sm font-semibold">{item.area}</p>
                  <p className="text-xs text-muted-foreground">
                    {item.type} · {item.size}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-bold">{item.price}</p>
                  <p className="text-xs" style={{ color: COLORS.CORAL }}>
                    {item.change}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 골든패스 프리셋 3종 — 입력만 채우고 정상 경로. (프로덕션 빌드에도 노출; VITE_HIDE_DEMO=1로 숨김 가능) */}
      {SHOW_DEMO_PRESETS && (
        <div className="px-5 pb-6">
          <p className="text-[11px] text-muted-foreground mb-1.5 text-right">
            🧪 데모 프리셋 · 입력만 채움, 계산은 정상 경로
          </p>
          <div className="flex justify-end gap-1.5 flex-wrap">
            {PERSONAS.map((p) => (
              <button
                key={p.id}
                onClick={() => loadPreset(p)}
                className="text-xs text-muted-foreground border border-border rounded-full px-3 py-1.5"
              >
                {p.id} · {p.label}
              </button>
            ))}
          </div>
        </div>
      )}

      <Toast message={toast || ""} visible={toast !== null} />
    </MobileShell>
  );
}
