// 외부 서비스 링크 헬퍼 — 발품을 '대체'가 아니라 '이어주는' 진입점.
//
// ⚠️ KB부동산(kbland.kr) 딥링크 쿼리 파라미터 스펙이 미확인이라, 추측성 파라미터로
//    죽은 링크를 만들지 않기 위해 **검증된 진입 URL(홈/지도 검색)** 로만 보낸다.
//    동네명은 링크 '텍스트'로 전달하고, 실제 쿼리 딥링크는 RESEARCH 항목(파라미터 확인 후 교체).
const KBLAND_ENTRY = 'https://kbland.kr/';

/** 동네 실매물을 KB부동산에서 이어보는 외부 링크(새 탭). 매물 데이터를 가져오지 않는다. */
export function kbLandUrl(_regionName?: string): string {
  // _regionName은 현재 URL에 싣지 않음(딥링크 파라미터 미검증). 진입점만 반환.
  return KBLAND_ENTRY;
}

// ── 금융상품 공식 페이지 (Q2) — 전부 실제 접속으로 검증한 URL만(추측 딥링크 금지) ──
//  · 버팀목/디딤돌 = 주택도시기금(nhuf.molit.go.kr) — 검증: 버팀목·디딤돌 상품 명시, 정상
//  · 반환보증 = HUG(khug.or.kr) 전세보증금반환보증 상품개요 — 검증: 정상
//  · KB 상품 = KB국민은행(kbstar.com) 공식 도메인(딥링크 미검증 → 베이스 진입만)
const OFFICIAL = {
  huf: 'https://nhuf.molit.go.kr/',
  hug: 'https://www.khug.or.kr/hug/web/ig/dr/igdr000001.jsp',
  kb: 'https://www.kbstar.com/',
};

/** 상품명 → 공식 페이지 URL. 매칭 없으면 null(링크 없이 이름만). */
export function officialProductUrl(name: string): string | null {
  const n = name || '';
  if (/버팀목|디딤돌/.test(n)) return OFFICIAL.huf;
  if (/반환보증|보증/.test(n)) return OFFICIAL.hug;
  if (/KB|전세대출|전세자금|주택담보|주담대/.test(n)) return OFFICIAL.kb;
  return null;
}
