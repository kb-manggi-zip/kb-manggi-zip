import type { Scene } from '../api/types';

export const SCENES_MOVE: Scene[] = [
  {
    time: '🌅 07:40',
    emoji: '🚶',
    visual: 'https://images.unsplash.com/photo-1555883006-0f5a0915a80f?w=390&h=500&fit=crop&auto=format',
    caption1: '역까지 도보 8분, 완만한 내리막',
    caption2: '상계역 4호선 직통, 시청까지 32분',
    basis: '실거래·경로 데이터 기준',
  },
  {
    time: '🌤 09:00',
    emoji: '☕',
    visual: 'https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?w=390&h=500&fit=crop&auto=format',
    caption1: '단지 앞 편의점 겸 카페',
    caption2: '아메리카노 2,500원, 매일 들리는 거리',
    basis: '네이버지도 기준',
  },
  {
    time: '☀️ 12:30',
    emoji: '🍱',
    visual: 'https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=390&h=500&fit=crop&auto=format',
    caption1: '반경 300m 식당 16곳',
    caption2: '점심 평균 9,800원대',
    basis: '카카오맵 기준',
  },
  {
    time: '🌇 18:30',
    emoji: '🛒',
    visual: 'https://images.unsplash.com/photo-1578916171728-46686eac8d58?w=390&h=500&fit=crop&auto=format',
    caption1: '도보 5분 대형마트',
    caption2: '주차 무료, 주말 혼잡',
    basis: '로드뷰 기준',
  },
  {
    time: '🌙 22:00',
    emoji: '🏠',
    visual: 'https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=390&h=500&fit=crop&auto=format',
    caption1: '방 2개, 남향, 관리비 9만원',
    caption2: '조용한 주택가, 밤 소음 적음',
    basis: '실거래 기준',
  },
];

export const SCENES_BUY: Scene[] = [
  {
    time: '🌅 07:20',
    emoji: '🚇',
    visual: 'https://images.unsplash.com/photo-1556075798-4825dfaaf498?w=390&h=500&fit=crop&auto=format',
    caption1: '합정역 2·6호선 환승, 도보 4분',
    caption2: '출근 피크타임 35분 여유',
    basis: '경로 데이터 기준',
  },
  {
    time: '☕ 08:30',
    emoji: '🏙',
    visual: 'https://images.unsplash.com/photo-1545093149-618ce3bcf49d?w=390&h=500&fit=crop&auto=format',
    caption1: '홍대·합정 카페 벨트 도보권',
    caption2: '매달 1곳씩 새 카페 오픈 중',
    basis: '네이버플레이스 기준',
  },
  {
    time: '🌤 13:00',
    emoji: '🌿',
    visual: 'https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=390&h=500&fit=crop&auto=format',
    caption1: '한강공원 도보 10분',
    caption2: '주말 피크닉 명소',
    basis: '로드뷰 기준',
  },
  {
    time: '🌆 19:00',
    emoji: '🍽',
    visual: 'https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=390&h=500&fit=crop&auto=format',
    caption1: '합정 먹자골목, 저녁 다양',
    caption2: '1인 평균 18,000원대',
    basis: '카카오맵 기준',
  },
  {
    time: '🌙 22:30',
    emoji: '🏡',
    visual: 'https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=390&h=500&fit=crop&auto=format',
    caption1: '방 2개 25평형, 남향 채광 우수',
    caption2: '내 집이 된 첫날 밤',
    basis: '실거래 기준',
  },
];

// 갱신 = 눌러앉기: 이사 없이 익숙한 동네 그대로의 하루
export const SCENES_STAY: Scene[] = [
  {
    time: '🌅 07:50',
    emoji: '🚶',
    visual: 'https://images.unsplash.com/photo-1555883006-0f5a0915a80f?w=390&h=500&fit=crop&auto=format',
    caption1: '3년째 그대로인 출근길',
    caption2: '역까지 도보 7분, 눈감고도 아는 길',
    basis: '현 계약 기준',
  },
  {
    time: '🌤 09:00',
    emoji: '☕',
    visual: 'https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?w=390&h=500&fit=crop&auto=format',
    caption1: '얼굴 아는 단골 카페',
    caption2: "'늘 마시던 걸로' 되는 아침",
    basis: '네이버지도 기준',
  },
  {
    time: '☀️ 12:30',
    emoji: '🍱',
    visual: 'https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=390&h=500&fit=crop&auto=format',
    caption1: '점심은 늘 가던 그 집',
    caption2: '새로 찾을 것 없는 익숙한 동네 밥집',
    basis: '카카오맵 기준',
  },
  {
    time: '🌇 18:30',
    emoji: '🛒',
    visual: 'https://images.unsplash.com/photo-1578916171728-46686eac8d58?w=390&h=500&fit=crop&auto=format',
    caption1: '장 보던 마트, 이웃과 인사',
    caption2: '익숙한 동선, 바뀌는 것 없음',
    basis: '로드뷰 기준',
  },
  {
    time: '🌙 22:00',
    emoji: '🏠',
    visual: 'https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=390&h=500&fit=crop&auto=format',
    caption1: '짐 안 싸도 되는 밤',
    caption2: '갱신으로 이사비·중개비 0원',
    basis: '현 계약 기준',
  },
];

// 지역별 override (regionId 기준). '-m'=월세 후보 → base 이사와 다른 동네별 하루.
// backend app/agents/scenes.yaml `regions`와 동기화 유지(compare.ts↔compare.py 규칙과 동일).
export const SCENES_BY_REGION: Record<string, Scene[]> = {
  // 마포구 망원동 (월세) — 한강공원·힙한거리
  'mapo-m': [
    {
      time: '🌅 07:40',
      emoji: '🚶',
      visual: 'https://images.unsplash.com/photo-1555883006-0f5a0915a80f?w=390&h=500&fit=crop&auto=format',
      caption1: '망원역 6호선 도보 6분',
      caption2: '합정 환승 없이 시청 28분',
      basis: '실거래·경로 데이터 기준',
    },
    {
      time: '🌤 09:00',
      emoji: '☕',
      visual: 'https://images.unsplash.com/photo-1545093149-618ce3bcf49d?w=390&h=500&fit=crop&auto=format',
      caption1: '망리단길 로스터리 카페 즐비',
      caption2: '골목마다 새 가게, 아메리카노 3,000원',
      basis: '네이버플레이스 기준',
    },
    {
      time: '☀️ 12:30',
      emoji: '🍜',
      visual: 'https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=390&h=500&fit=crop&auto=format',
      caption1: '망원시장 칼국수·닭강정 노포',
      caption2: '점심 7,000원대, 시장 활기',
      basis: '카카오맵 기준',
    },
    {
      time: '🌇 18:30',
      emoji: '🏞',
      visual: 'https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=390&h=500&fit=crop&auto=format',
      caption1: '한강공원 망원지구 자전거 5분',
      caption2: '저녁 러닝·피크닉 명소',
      basis: '로드뷰 기준',
    },
    {
      time: '🌙 22:00',
      emoji: '🏠',
      visual: 'https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=390&h=500&fit=crop&auto=format',
      caption1: '투룸 월세 195만 안팎',
      caption2: '밤에도 사람 많은 힙한 골목',
      basis: '실거래 기준',
    },
  ],
  // 서대문구 홍제동 (월세) — 산책로·재래시장
  'seodaemun-m': [
    {
      time: '🌅 07:45',
      emoji: '🚶',
      visual: 'https://images.unsplash.com/photo-1555883006-0f5a0915a80f?w=390&h=500&fit=crop&auto=format',
      caption1: '홍제역 3호선 도보 9분',
      caption2: '광화문 버스 20분, 환승 적음',
      basis: '실거래·경로 데이터 기준',
    },
    {
      time: '🌤 09:00',
      emoji: '🌿',
      visual: 'https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=390&h=500&fit=crop&auto=format',
      caption1: '홍제천 산책로 문 앞',
      caption2: '인왕산 자락길 주말 등산',
      basis: '로드뷰 기준',
    },
    {
      time: '☀️ 12:30',
      emoji: '🥘',
      visual: 'https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=390&h=500&fit=crop&auto=format',
      caption1: '인왕시장 백반·분식 골목',
      caption2: '점심 6,500원대, 정겨운 노포',
      basis: '카카오맵 기준',
    },
    {
      time: '🌇 18:30',
      emoji: '🛒',
      visual: 'https://images.unsplash.com/photo-1578916171728-46686eac8d58?w=390&h=500&fit=crop&auto=format',
      caption1: '재래시장 장보기 도보 5분',
      caption2: '제철 채소·반찬 저렴',
      basis: '로드뷰 기준',
    },
    {
      time: '🌙 22:00',
      emoji: '🏠',
      visual: 'https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=390&h=500&fit=crop&auto=format',
      caption1: '투룸 월세 180만 안팎',
      caption2: '조용한 언덕 주택가, 밤 한적',
      basis: '실거래 기준',
    },
  ],
  // 성북구 보문동 (월세) — 카페거리·대학가
  'seongbuk-m': [
    {
      time: '🌅 07:50',
      emoji: '🚇',
      visual: 'https://images.unsplash.com/photo-1556075798-4825dfaaf498?w=390&h=500&fit=crop&auto=format',
      caption1: '보문역 6호선·우이신설 더블역세권',
      caption2: '성신여대·고려대 통학권',
      basis: '경로 데이터 기준',
    },
    {
      time: '🌤 09:00',
      emoji: '☕',
      visual: 'https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?w=390&h=500&fit=crop&auto=format',
      caption1: '대학가 카페거리 도보권',
      caption2: '스터디카페·브런치 다양',
      basis: '네이버플레이스 기준',
    },
    {
      time: '☀️ 12:30',
      emoji: '🍱',
      visual: 'https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=390&h=500&fit=crop&auto=format',
      caption1: '가성비 학식·백반 밀집',
      caption2: '점심 7,000원 안팎',
      basis: '카카오맵 기준',
    },
    {
      time: '🌆 18:30',
      emoji: '🍽',
      visual: 'https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=390&h=500&fit=crop&auto=format',
      caption1: '젊은 상권, 저녁 다양',
      caption2: '1인 15,000원대',
      basis: '카카오맵 기준',
    },
    {
      time: '🌙 22:00',
      emoji: '🏠',
      visual: 'https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=390&h=500&fit=crop&auto=format',
      caption1: '원룸 월세 170만 안팎',
      caption2: '대학가 활기, 편의시설 밀집',
      basis: '실거래 기준',
    },
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
