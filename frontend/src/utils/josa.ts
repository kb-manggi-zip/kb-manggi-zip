// 한글 조사 자동 선택 — 마지막 글자 받침(종성) 유무로 은/는·을/를·이/가 분기.
// 하드코딩된 "은(는)" 류 제거용. 한글 음절이 아니면 받침 없음으로 취급.
function hasBatchim(word: string): boolean {
  const w = word.trim();
  if (!w) return false;
  const c = w.charCodeAt(w.length - 1);
  if (c < 0xac00 || c > 0xd7a3) return false; // 한글 음절 아님(숫자·영문·기호) → 받침 없음 취급
  return (c - 0xac00) % 28 !== 0;             // 종성 인덱스 0 = 받침 없음
}

export function josa(word: string, withBatchim: string, without: string): string {
  return hasBatchim(word) ? withBatchim : without;
}

// 자주 쓰는 짝 — `${word}${eunNeun(word)}` 형태로 사용
export const eunNeun = (w: string) => josa(w, '은', '는');
export const eulReul = (w: string) => josa(w, '을', '를');
export const iGa = (w: string) => josa(w, '이', '가');
