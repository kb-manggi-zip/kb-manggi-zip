export const COLORS = {
  KB_YELLOW: '#FFBC00',
  YELLOW_SOFT: '#FFE9A8',
  YELLOW_SURFACE: '#FFF7E0',
  KB_GRAY: '#60584C',
  BG: '#FFFDF8',
  CARD: '#FFFFFF',
  TEXT: '#1F2024',
  SUB: '#6B7280',
  BORDER: '#EDE7D8',
  BLUE: '#5B8DEF',
  MINT: '#7ED9A6',
  CORAL: '#FF8A70',
} as const;

export const BRANCH_COLORS = {
  갱신: COLORS.MINT,
  이사: COLORS.BLUE,
  매매: COLORS.KB_YELLOW,
} as const;

export const BRANCH_ICONS = {
  갱신: '🏠',
  이사: '🚚',
  매매: '🔑',
} as const;

// ─── 타이포 스케일 ─────────────────────────────────────────────────────────
// text-[9px]~text-3xl까지 화면마다 제각각 쓰이던 걸 5단계로 정리. 색상은 안 담아(text-muted-foreground 등과 조합해 쓴다).
export const TYPE = {
  caption: 'text-[11px] leading-snug', // 각주·타임스탬프·보조 설명
  body: 'text-xs leading-snug', // 기본 본문·태그·리스트 항목
  bodyStrong: 'text-sm leading-snug', // 서브타이틀·강조 설명
  heading: 'text-base font-bold', // 카드·섹션 제목
  display: 'text-2xl font-bold', // 핵심 숫자 강조(금액 헤드라인)
} as const;

// ─── 카드 내부 버튼 크기 스케일 ────────────────────────────────────────────
// 화면 전체 CTA는 PrimaryBtn/SecondaryBtn(h-14)를 쓰고, 카드 하나 안에 여러 버튼이 있을 땐 이 크기로 통일한다.
// 주·보조 행동은 크기가 아니라 채움(배경색)으로만 구분 — 크기까지 다르면 하나만 튀어 보인다(2026-08-01).
export const BTN = {
  card: 'h-9 rounded-xl text-xs font-medium',
} as const;
