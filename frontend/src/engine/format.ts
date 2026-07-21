// 모든 화면에서 이 유틸만 사용 — 직접 숫자 포맷 금지
export function formatAmount(won: number): string {
  if (won >= 100_000_000) {
    const eok = won / 100_000_000;
    const man = Math.round((won % 100_000_000) / 10_000);
    if (man === 0) return `${eok.toFixed(0)}억`;
    return `${Math.floor(eok)}억 ${man.toLocaleString()}만`;
  }
  if (won >= 10_000) {
    return `${Math.round(won / 10_000).toLocaleString()}만`;
  }
  return won.toLocaleString() + '원';
}

export function formatMonthly(won: number): string {
  if (won >= 10_000) return `월 ${Math.round(won / 10_000)}만원`;
  return `월 ${won.toLocaleString()}원`;
}

export function formatComma(won: number): string {
  return won.toLocaleString();
}

export function formatKorean(won: number): string {
  const eok = Math.floor(won / 100_000_000);
  const man = Math.round((won % 100_000_000) / 10_000);
  if (eok > 0 && man > 0) return `${eok}억 ${man.toLocaleString()}만원`;
  if (eok > 0) return `${eok}억원`;
  if (man > 0) return `${man.toLocaleString()}만원`;
  return '0원';
}

export function parsePriceInput(raw: string): number {
  return parseInt(raw.replace(/,/g, '').replace(/[^0-9]/g, ''), 10) || 0;
}

export function formatDday(expiryDate: string): number {
  const now = new Date();
  const expiry = new Date(expiryDate);
  return Math.ceil((expiry.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
}

export function formatNoticeDeadline(expiryDate: string, months: number): Date {
  const expiry = new Date(expiryDate);
  expiry.setMonth(expiry.getMonth() - months);
  return expiry;
}

export function formatDate(date: Date): string {
  return `${date.getFullYear()}.${String(date.getMonth() + 1).padStart(2, '0')}.${String(date.getDate()).padStart(2, '0')}`;
}
