// 외부 서비스 링크 헬퍼 — 발품을 '대체'가 아니라 '이어주는' 진입점.
//
// KB부동산(kbland.kr) 지도는 `xy=위도,경도,줌레벨` 쿼리로 해당 좌표로 이동한다
// (2026-07-29 실브라우저로 직접 확인: 마포구 합정동 좌표 → 합정역 인근 지도로 정상 이동).
const KBLAND_ENTRY = 'https://kbland.kr/';

/** 동네 실매물을 KB부동산 지도(해당 좌표)에서 이어보는 외부 링크(새 탭). 매물 데이터를 가져오지 않는다. */
export function kbLandUrl(lat?: number, lng?: number): string {
  if (lat == null || lng == null) return KBLAND_ENTRY;
  return `${KBLAND_ENTRY}?xy=${lat},${lng},17`;
}

// ── 금융상품 공식 페이지 (Q2) — 전부 실제 접속으로 검증한 URL만(추측 딥링크 금지) ──
// backend/data/kb_products/*.md의 source_url과 동일한 값(수동 동기화 — API에 아직 url 필드 없음, 2026-07-29).
//  · 청년전용 버팀목/디딤돌 = 주택도시기금(nhuf.molit.go.kr) 상품별 페이지 — 검증됨
//  · 반환보증 = HUG(khug.or.kr) 전세보증금반환보증 상품개요 — 검증됨
//  · KB 전세자금대출/주택담보대출/청약담보대출 = obank.kbstar.com 상품 상세(prcode 딥링크) — 2026-07-29 실브라우저 검증됨
//  · 화재보험 = kbinsure.co.kr 베이스만(상품별 딥링크 미검증)
const OFFICIAL = {
  buttimokYouth: 'https://nhuf.molit.go.kr/FP/FP05/FP0502/FP05020301.jsp', // 청년전용 버팀목 전세자금
  didimdol: 'https://nhuf.molit.go.kr/FP/FP05/FP0503/FP05030104.jsp', // 내집마련 디딤돌대출
  hug: 'https://www.khug.or.kr/hug/web/ig/dr/igdr000001.jsp', // 전세보증금 반환보증
  kbJeonse: 'https://obank.kbstar.com/quics?page=C103507&cc=b104363:b104516&isNew=N&prcode=LN20000026&QSL=F', // KB 전세자금대출
  kbMortgage: 'https://obank.kbstar.com/quics?page=C103557&cc=b104363:b104516&isNew=N&prcode=LN20001160&QSL=F', // KB 주택담보대출
  kbChungyak: 'https://obank.kbstar.com/quics?page=C103557&isNew=N&prcode=LN20000065&QSL=F', // 주택청약종합저축(담보대출)
  fireInsurance: 'https://www.kbinsure.co.kr', // 화재보험
};

/** 상품명 → 공식 페이지 URL. 매칭 없으면 null(링크 없이 이름만). */
export function officialProductUrl(name: string): string | null {
  const n = name || '';
  if (/청년전용 버팀목|버팀목/.test(n)) return OFFICIAL.buttimokYouth;
  if (/디딤돌/.test(n)) return OFFICIAL.didimdol;
  if (/반환보증/.test(n)) return OFFICIAL.hug;
  if (/청약/.test(n)) return OFFICIAL.kbChungyak;
  if (/화재보험/.test(n)) return OFFICIAL.fireInsurance;
  if (/전세대출|전세자금/.test(n)) return OFFICIAL.kbJeonse;
  if (/주택담보|주담대/.test(n)) return OFFICIAL.kbMortgage;
  return null;
}
