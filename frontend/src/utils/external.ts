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
