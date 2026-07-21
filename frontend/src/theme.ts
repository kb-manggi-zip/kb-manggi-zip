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
