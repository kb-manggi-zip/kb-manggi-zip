import type { CompareResponse, Region } from '../api/types';
import { formatAmount } from '../utils/format';

function lightest(c: CompareResponse): string {
  const sorted = [...c.branches].sort((a, b) => a.monthlyBurden - b.monthlyBurden);
  return sorted[0].branch;
}

function buyMonthly(c: CompareResponse): string {
  const b = c.branches.find(br => br.branch === '매매');
  return b ? formatAmount(b.monthlyBurden) : '-';
}

function renewalMonthly(c: CompareResponse): string {
  const b = c.branches.find(br => br.branch === '갱신');
  return b ? formatAmount(b.monthlyBurden) : '-';
}

// 갈래별 '구조 특성' 한 줄 — 서술만(권유·이득 표현 금지). 리포트 관점 선언에서 재사용.
const BRANCH_STRUCTURAL: Record<string, string> = {
  매매: '매매는 월 부담이 크지만 상환액 일부가 이자가 아니라 자산으로 남아요',
  이사: '이사는 보증금·이사비 같은 일회성 비용이 들지만 조건이 더 맞는 동네로 옮길 수 있어요',
  갱신: '갱신은 이사비·발품 없이 익숙한 동네를 이어가지만 오른 보증금만큼 목돈이 묶여요',
};

// ⚠️ 문장 규칙: "추천합니다/하세요/이득" 금지. 서술만.
export const briefings = {
  // 리포트 관점 선언 + 비교 잔상(결정론 조립·LLM 없음). 값은 전부 compare 결과 재사용.
  // fmt = 화면과 동일한 금액 포맷터(man)를 주입해 표기 일관성 유지.
  reportPerspective: (c: CompareResponse, branch: string, fmt: (won: number) => string): { declare: string; contrast: string } => {
    const others = c.branches.filter(b => b.branch !== branch);
    const otherStr = others.map(b => `${b.branch} ${fmt(b.monthlyBurden)}`).join(' · ');
    const structural = BRANCH_STRUCTURAL[branch] ?? '';
    return {
      declare: `선택하신 ${branch} 기준의 리포트예요.`,
      contrast: otherStr
        ? `${otherStr}과 비교하면, ${structural}.`
        : (structural ? `${structural}.` : ''),
    };
  },

  compare: (c: CompareResponse, name: string): string =>
    `${name}님, 세 경우를 계산했어요. 매달 부담만 보면 ${lightest(c)}가 가장 가볍지만, ` +
    `사기의 월 ${buyMonthly(c)} 중 일부는 이자가 아니라 자산으로 쌓여요. ` +
    `어느 쪽이 맞는지는 ${name}님의 계획에 달려 있어요.`,

  regions: (top: Region): string =>
    `최근 실거래를 기준으로 예산에 맞는 동네를 추렸어요. ` +
    (top.surplus > 0
      ? `${top.name}은 예산 대비 ${formatAmount(top.surplus)} 여유가 있어요.`
      : `${top.name}부터 둘러보시겠어요?`),

  renewal: (noticeDate: string): string =>
    `눌러앉기를 고르셨네요. 통보 기한(${noticeDate})까지 챙길 것 네 가지를 정리했어요.`,

  revisit: (daysCloser: number): string =>
    `지난번 계산 이후 만기가 ${daysCloser}일 더 가까워졌어요.`,

  dayPlayer: (regionName: string): string =>
    `${regionName}에서의 하루를 만들었어요.`,

  savedMoney: (): string =>
    `눌러앉으면 아끼는 돈의 쓰임을 정리했어요.`,

  finance: (branch: string, reason: string): string =>
    `${branch} 경로에 맞는 상품을 골랐어요. ${reason}`,
};
