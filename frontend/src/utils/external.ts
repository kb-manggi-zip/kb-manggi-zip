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
// 정부(주택도시기금) 페이지 대신, 우리 서비스가 KB를 이어주는 것이므로 KB 자체 신청 페이지로 통일.
// backend/data/kb_products/*.md의 source_url도 이 값으로 같이 갱신 필요(2026-07-29 기준 아직 미동기화).
//  · 버팀목/디딤돌 = obank.kbstar.com 주택도시기금대출 카테고리 내 상품별 페이지 — 2026-07-29 실브라우저 검증됨
//  · 반환보증 = obank.kbstar.com 전세보증금반환보증(단독) 상품 상세 — 2026-07-29 실브라우저 검증됨
//  · KB 전세자금대출/주택담보대출/청약담보대출 = obank.kbstar.com 상품 상세(prcode 딥링크) — 2026-07-29 실브라우저 검증됨
//  · 화재보험 = KB손해보험(kbinsure.co.kr) — 2026-07-29 실브라우저 검증됨(단, 상품소개가 아니라 "화재 발생 시 대처 안내" 페이지)
const OFFICIAL = {
  buttimokYouth: 'https://obank.kbstar.com/quics?page=C103998&cc=b104363:b104516&브랜드상품코드=LN20000313&노드코드=00019&prcode=LN20000313', // 청년전용 버팀목 전세자금(KB)
  didimdol: 'https://obank.kbstar.com/quics?page=C103998&cc=b104363:b104516&브랜드상품코드=LN20000300&노드코드=00019&prcode=LN20000300', // 내집마련 디딤돌대출(KB)
  hug: 'https://obank.kbstar.com/quics?page=C103507&cc=b104363:b104516&isNew=N&prcode=LN35000559&QSL=F', // 전세보증금반환보증(단독, KB)
  kbJeonse: 'https://obank.kbstar.com/quics?page=C103507&cc=b104363:b104516&isNew=N&prcode=LN20000026&QSL=F', // KB 전세자금대출
  kbMortgage: 'https://obank.kbstar.com/quics?page=C103557&cc=b104363:b104516&isNew=N&prcode=LN20001160&QSL=F', // KB 주택담보대출
  kbChungyak: 'https://obank.kbstar.com/quics?page=C103557&isNew=N&prcode=LN20000065&QSL=F', // 주택청약종합저축(담보대출)
  fireInsurance: 'https://www.kbinsure.co.kr/CG305030001.ec', // 화재보험 — 화재 발생 시 대처 안내 페이지
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
