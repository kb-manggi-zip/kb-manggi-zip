import type { Scene } from '../api/types';

// ⚠️ Trust Layer(L1): 씬 캡션은 (a) 공공 랜드마크 명칭, (b) 지하철 노선 공개정보,
//    (c) 시간대·동선 중립 연결어로만. 가격·비용·상태(활기/노포/즐비/소음 등) 단정 금지.
//    실측 수치(통근·상권·실거래)는 발품 하단 내레이션(narrator)과 fact 칩이 담당한다.
//    backend app/agents/scenes.yaml 과 내용 동기화 유지.

export const SCENES_MOVE: Scene[] = [
  { time: '🌅 07:40', emoji: '🚶', visual: 'https://images.unsplash.com/photo-1555883006-0f5a0915a80f?w=390&h=500&fit=crop&auto=format', caption1: '아침, 지하철역으로 향하는 길', caption2: '새 동네에서 맞는 첫 출근', basis: '하루 흐름 예시' },
  { time: '🌤 09:00', emoji: '☕', visual: 'https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?w=390&h=500&fit=crop&auto=format', caption1: '동네 카페에서 여는 하루', caption2: '', basis: '하루 흐름 예시' },
  { time: '☀️ 12:30', emoji: '🍱', visual: 'https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=390&h=500&fit=crop&auto=format', caption1: '가까운 식당가에서 점심', caption2: '', basis: '하루 흐름 예시' },
  { time: '🌇 18:30', emoji: '🛒', visual: 'https://images.unsplash.com/photo-1578916171728-46686eac8d58?w=390&h=500&fit=crop&auto=format', caption1: '퇴근길, 마트 들러 장보기', caption2: '', basis: '하루 흐름 예시' },
  { time: '🌙 22:00', emoji: '🏠', visual: 'https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=390&h=500&fit=crop&auto=format', caption1: '새 집에서 맞는 밤', caption2: '', basis: '하루 흐름 예시' },
];

export const SCENES_BUY: Scene[] = [
  { time: '🌅 07:20', emoji: '🚇', visual: 'https://images.unsplash.com/photo-1556075798-4825dfaaf498?w=390&h=500&fit=crop&auto=format', caption1: '아침, 지하철로 출근', caption2: '', basis: '하루 흐름 예시' },
  { time: '☕ 08:30', emoji: '🏙', visual: 'https://images.unsplash.com/photo-1545093149-618ce3bcf49d?w=390&h=500&fit=crop&auto=format', caption1: '동네 카페 거리를 지나며', caption2: '', basis: '하루 흐름 예시' },
  { time: '🌤 13:00', emoji: '🌿', visual: 'https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=390&h=500&fit=crop&auto=format', caption1: '가까운 공원에서 잠깐', caption2: '', basis: '하루 흐름 예시' },
  { time: '🌆 19:00', emoji: '🍽', visual: 'https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=390&h=500&fit=crop&auto=format', caption1: '저녁, 동네 먹자골목', caption2: '', basis: '하루 흐름 예시' },
  { time: '🌙 22:30', emoji: '🏡', visual: 'https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=390&h=500&fit=crop&auto=format', caption1: '내 집이 된 첫날 밤', caption2: '', basis: '하루 흐름 예시' },
];

// 갱신 = 눌러앉기: 이사 없이 익숙한 동네 그대로의 하루(연속성 표현 — 특정 장소 사실 단정 아님)
export const SCENES_STAY: Scene[] = [
  { time: '🌅 07:50', emoji: '🚶', visual: 'https://images.unsplash.com/photo-1555883006-0f5a0915a80f?w=390&h=500&fit=crop&auto=format', caption1: '늘 걷던 출근길', caption2: '눈감고도 아는 길', basis: '현 계약 유지' },
  { time: '🌤 09:00', emoji: '☕', visual: 'https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?w=390&h=500&fit=crop&auto=format', caption1: '늘 가던 동네 카페', caption2: '', basis: '현 계약 유지' },
  { time: '☀️ 12:30', emoji: '🍱', visual: 'https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=390&h=500&fit=crop&auto=format', caption1: '점심은 늘 가던 그 집', caption2: '', basis: '현 계약 유지' },
  { time: '🌇 18:30', emoji: '🛒', visual: 'https://images.unsplash.com/photo-1578916171728-46686eac8d58?w=390&h=500&fit=crop&auto=format', caption1: '장 보던 익숙한 마트', caption2: '', basis: '현 계약 유지' },
  { time: '🌙 22:00', emoji: '🏠', visual: 'https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=390&h=500&fit=crop&auto=format', caption1: '짐 안 싸도 되는 밤', caption2: '갱신으로 이사비·중개비 0원', basis: '현 계약 유지' },
];

// 지역별 override (regionId 기준). '-m'=월세 후보 → 동네별 하루. 공공 랜드마크 명칭만 유지, 가격·상태 단정 제거.
// backend app/agents/scenes.yaml `regions`와 동기화 유지.
export const SCENES_BY_REGION: Record<string, Scene[]> = {
  // 마포구 망원동 (월세) — 한강공원·망리단길·망원시장(공공 랜드마크)
  'mapo-m': [
    { time: '🌅 07:40', emoji: '🚶', visual: 'https://images.unsplash.com/photo-1555883006-0f5a0915a80f?w=390&h=500&fit=crop&auto=format', caption1: '망원역 6호선, 도보권', caption2: '', basis: '지하철 노선 공개정보' },
    { time: '🌤 09:00', emoji: '☕', visual: 'https://images.unsplash.com/photo-1545093149-618ce3bcf49d?w=390&h=500&fit=crop&auto=format', caption1: '망리단길 카페 거리', caption2: '', basis: '동네 분위기 예시' },
    { time: '☀️ 12:30', emoji: '🍜', visual: 'https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=390&h=500&fit=crop&auto=format', caption1: '망원시장 먹거리 골목', caption2: '', basis: '동네 분위기 예시' },
    { time: '🌇 18:30', emoji: '🏞', visual: 'https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=390&h=500&fit=crop&auto=format', caption1: '한강공원 망원지구 가까이', caption2: '', basis: '동네 분위기 예시' },
    { time: '🌙 22:00', emoji: '🏠', visual: 'https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=390&h=500&fit=crop&auto=format', caption1: '망원동에서 맞는 밤', caption2: '', basis: '하루 흐름 예시' },
  ],
  // 서대문구 홍제동 (월세) — 홍제천·인왕산·인왕시장(공공 랜드마크)
  'seodaemun-m': [
    { time: '🌅 07:45', emoji: '🚶', visual: 'https://images.unsplash.com/photo-1555883006-0f5a0915a80f?w=390&h=500&fit=crop&auto=format', caption1: '홍제역 3호선, 도보권', caption2: '', basis: '지하철 노선 공개정보' },
    { time: '🌤 09:00', emoji: '🌿', visual: 'https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=390&h=500&fit=crop&auto=format', caption1: '홍제천 산책로 · 인왕산 자락길', caption2: '', basis: '동네 분위기 예시' },
    { time: '☀️ 12:30', emoji: '🥘', visual: 'https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=390&h=500&fit=crop&auto=format', caption1: '인왕시장 먹거리 골목', caption2: '', basis: '동네 분위기 예시' },
    { time: '🌇 18:30', emoji: '🛒', visual: 'https://images.unsplash.com/photo-1578916171728-46686eac8d58?w=390&h=500&fit=crop&auto=format', caption1: '재래시장 장보기', caption2: '', basis: '동네 분위기 예시' },
    { time: '🌙 22:00', emoji: '🏠', visual: 'https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=390&h=500&fit=crop&auto=format', caption1: '홍제동에서 맞는 밤', caption2: '', basis: '하루 흐름 예시' },
  ],
  // 성북구 보문동 (월세) — 보문역·성신여대·고려대(공공 랜드마크)
  'seongbuk-m': [
    { time: '🌅 07:50', emoji: '🚇', visual: 'https://images.unsplash.com/photo-1556075798-4825dfaaf498?w=390&h=500&fit=crop&auto=format', caption1: '보문역 6호선·우이신설', caption2: '성신여대·고려대 인접', basis: '지하철 노선 공개정보' },
    { time: '🌤 09:00', emoji: '☕', visual: 'https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?w=390&h=500&fit=crop&auto=format', caption1: '대학가 카페 거리', caption2: '', basis: '동네 분위기 예시' },
    { time: '☀️ 12:30', emoji: '🍱', visual: 'https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=390&h=500&fit=crop&auto=format', caption1: '학식·백반 골목', caption2: '', basis: '동네 분위기 예시' },
    { time: '🌆 18:30', emoji: '🍽', visual: 'https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=390&h=500&fit=crop&auto=format', caption1: '대학가 상권', caption2: '', basis: '동네 분위기 예시' },
    { time: '🌙 22:00', emoji: '🏠', visual: 'https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=390&h=500&fit=crop&auto=format', caption1: '보문동에서 맞는 밤', caption2: '', basis: '하루 흐름 예시' },
  ],
};

export const SAVED_MONEY_CARDS = [
  {
    title: '이사 안 하면 일회성 비용을 아껴요',
    icon: '💰',
    body: '이사비·중개비·새 보증금 마련 부담 없이 지금 집에서 2년 더.',
  },
  {
    title: '이 돈이면 예적금 원금이 돼요',
    icon: '🏦',
    body: '아낀 비용을 정기예금 2년 상품에 넣으면 만기 시 원금+이자.',
    sub: '금리 연 3.8% 기준',
  },
  {
    title: '청약 납입 여유분이 생겨요',
    icon: '📋',
    body: '매달 10만원 이상 추가 납입하면 청약 당첨 가점에 도움.',
    sub: '청약 납입 횟수·금액 기준',
  },
  {
    title: '반환보증 N년치를 낼 수 있어요',
    icon: '🛡',
    body: '보증료 연 환산 기준, 아낀 비용으로 전세기간 내내 보증을 유지할 수 있어요.',
    sub: '보증기관 공시 요율 기준',
  },
];
