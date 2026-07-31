"""Pydantic 스키마 — 프론트 src/api/types.ts 와 1:1 계약.

⚠️ 임의 변경 금지. types.ts 가 계약서다. 필드명·타입·한글 리터럴을 그대로 유지한다.
변경이 필요하면 중단하고 사람에게 보고.

대조표 (types.ts interface ↔ 이 파일):
  ContractInfo        ↔ ContractInfo
  FinanceInfo         ↔ FinanceInfo
  BranchResult        ↔ BranchResult
  CompareResponse     ↔ CompareResponse
  Region              ↔ Region
  Scene               ↔ Scene
  SimulateResponse    ↔ SimulateResponse
  Product             ↔ Product
  ProductsResponse    ↔ ProductsResponse
  ReservationRequest  ↔ ReservationRequest
  BriefingRequest     ↔ BriefingRequest
  BriefingResponse    ↔ BriefingResponse
  DraftNoticeRequest  ↔ DraftNoticeRequest
  DraftNoticeResponse ↔ DraftNoticeResponse
  (types.ts interface 14개 = 이 파일 응답/공유 모델 14개)
  + 요청 래퍼(CompareRequest / SimulateRequest / ProductsRequest): 엔드포인트 body용
"""

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel


# ── 갱신 상황 enum (7개, 닫힘) — 자유입력을 AI가 이 목록으로만 분류. 목록 밖 값 생성 금지 ──
class RenewalSituation(str, Enum):
    notice_deadline_passed = "notice_deadline_passed"  # 통보기한 경과 → 묵시적 갱신(cap 0)
    renewal_right_exhausted = "renewal_right_exhausted"  # 갱신요구권 소진 → 5% 상한 미적용 가능
    jeonse_to_monthly = "jeonse_to_monthly"  # 전세→월세 전환 요구 → 전월세전환율 상한
    landlord_self_occupancy = "landlord_self_occupancy"  # 임대인 실거주 → 계산 불변, 안내만
    term_change = "term_change"  # 계약기간 변경 → 계산 불변, 안내만
    simple_increase = "simple_increase"  # 단순 합의 인상 → cap 5(기본)
    unknown = "unknown"  # 분류 불가 → 계산 미반영, consultNote 창구


# ── 타입 별칭 (types.ts 리터럴 유니온) ──────────────────────────────
ContractType = Literal["전세", "월세"]
RenewalUsed = Literal["미사용", "사용", "모름"]
HousingType = Literal[
    "아파트", "연립다세대"
]  # 국토부 API property_type과 동일 값. 화면엔 "원룸·투룸·빌라"로 표시. 둘 다 법적 '주택'
Household = Literal["1인", "신혼", "자녀"]
FirstHome = Literal["예", "아니오", "모름"]
Branch = Literal["갱신", "이사", "매매"]
BriefingKind = Literal["compare", "regions", "renewal", "revisit", "dayPlayer", "savedMoney", "finance"]


# ── 입력 ────────────────────────────────────────────────────────────
class ContractInfo(BaseModel):
    type: ContractType
    deposit: int
    monthlyRent: int
    expiryDate: str  # ISO date string
    renewalUsed: RenewalUsed
    housingType: HousingType = "아파트"  # HUG 보증료 요율만 좌우(세금·대출은 둘 다 주택 동일)
    preferredArea: str = ""  # 선호지역 구명(예 "마포구") — 동네 후보를 그 구에서 우선. 빈값=6구 전체
    note: str = ""  # 문진 말미 자유입력(선택) — 명확화 노드가 세그먼트·우선순위 항목으로 제약 해석
    noteAdjust: dict = {}  # HITL로 확정된 축별 배수(자연어 해석 확정분). 있으면 랭킹이 이걸 씀(결정론)
    renewalAskPct: Optional[int] = None  # 집주인이 요구한 갱신 인상률(%). 확정분만 — None이면 기존 5% 상한 동작 불변
    consultNote: str = ""  # 계산 불가한 사정(원문 그대로) — 상담사에게 전달. LLM 요약·재작성 금지
    renewalSituations: list[
        RenewalSituation
    ] = []  # HITL 확정된 갱신 상황. 빈 리스트면 기존 동작 불변(resolver가 simple_increase 기본)


class FinanceInfo(BaseModel):
    annualIncome: int
    ownCapital: int
    household: Household
    firstHome: FirstHome = "모름"  # 생애최초 주택구입 여부 (B1.5)
    under35: bool = False  # 만 35세 미만 (버팀목 청년 자격) (B1.5)


# ── 비교표 (심장) ───────────────────────────────────────────────────
class BranchResult(BaseModel):
    branch: Branch
    headline: str
    depositOrPrice: int
    loanAmount: int
    oneTimeCost: int
    guaranteeMonthly: int
    monthlyBurden: int
    risks: list[str]
    cares: list[str]
    basis: list[str]
    uncertainty: Optional[str] = None
    feature: str


class CompareResponse(BaseModel):
    branches: list[BranchResult]
    dday: int
    noticeDaysLeft: int
    noticeDeadline: str
    monthlyToDeposit: int  # 월세→보증금 환산 (월세만)
    savings: int  # 갱신 시 아끼는 일회성 비용
    assumptions: list[str]


# ── 동네 ────────────────────────────────────────────────────────────
class JeonseRatio(BaseModel):
    """전세가율 리스크 지표 — 보증금 ÷ 같은 동 매매 중위가(실거래). 예측 아님."""

    ratio: float  # 0.87 = 87%
    saleMedian: int  # 동 매매 중위가(원)
    sampleCount: int  # 매매 표본 수
    band: str  # safe | caution | alert
    label: str  # 구간 안내 문구
    basis: str  # "최근 6개월 …동 매매 N건 중위가 기준"


class Region(BaseModel):
    id: str
    name: str
    midPrice: int
    monthlyMidPrice: Optional[int] = None
    surplus: int
    tradeCount: int
    tags: list[str]
    lat: float
    lng: float
    branch: Branch
    score: Optional[float] = None  # 개인화 스코어(통계근거 가중합)
    scoreReasons: list[str] = []  # 왜 이 순위 (근거 노출)
    jeonseRatio: Optional[JeonseRatio] = None  # 전세 후보일 때 전세가율 리스크 지표(표본<5면 None)
    sigunguCode: Optional[str] = None  # 시군구코드 — 동 facts 없을 때 구 단위 상권/통근 폴백용(내부)


# ── 명확화(판단 노드) + 개인화 조합 레이어 ─────────────────────────
class ConflictItem(BaseModel):
    """상충 1건 — 인라인 해소(K1)용 구조. 상충하는 두 신호 + 되묻는 질문.

    type='axis'(두 문장이 같은 축 반대) / 'household'(가구 유형 불일치) / 'intra'(한 문장 내부 상충).
    optionA/optionB = axis·intra면 문장 원문, household면 가구 유형 '값'('1인'|'신혼'|'자녀').
    """

    type: str = "axis"
    axis: str = ""  # axis 상충일 때 어느 축인지
    optionA: str
    optionB: str = ""
    question: str
    allowBoth: bool = True  # '둘 다 맞아요' 허용(가구 유형 상충은 False)


class ClarifyResult(BaseModel):
    """문진 명확화 노드 산출 — 자연어/폼값을 '제약된 항목'으로 해석 + 모순 감지.

    판단 노드지만 창작 금지: persona/priorities는 정해진 세그먼트·축에서만 나온다.
    conflicts/questions는 되묻기(닫힌 루프)용 — 실제 재질의는 프론트가 처리.
    """

    persona: str  # 확정 세그먼트 라벨 (예 "1인 청년 임차")
    weightAdjust: dict = {}  # 이 입력의 적용 boost(축별 배수) — HITL 확정 시 랭킹에 실림
    held: bool = False  # 상충 미해결 → 자동 반영 보류('확인 대기'). 확정 전 랭킹 미반영
    mode: str = "rule"  # 검증 경로: 'ai'(LLM 의미검증) | 'rule'(키워드 간이검증, 폴백)
    priorities: list[str]  # 우선순위 축 라벨 순서 (스코어 가중치 상위)
    conflicts: list[str] = []  # 감지된 모순(질문 문자열) — 하위호환
    conflictItems: list[ConflictItem] = []  # 인라인 해소용 구조(K1/K4)
    questions: list[str] = []  # 되물을 질문(닫힌 루프)
    noteSignals: list[str] = []  # 자유입력에서 뽑아낸 제약된 신호(반영 내역)
    renewalAskPct: Optional[int] = None  # 자유입력에서 추출한 갱신 인상률 '제안'(%). 확정 전엔 계산 미반영
    consultNote: str = ""  # 4축·인상률로 해석 못한 갱신·주거 사정(원문). 상담 전달용 — 요약 금지
    renewalSituations: list[RenewalSituation] = []  # AI가 닫힌 enum으로 분류한 갱신 상황 '제안'. 확정 전 계산 미반영
    situationEvidence: dict[str, str] = {}  # 상황 id → 사용자 원문 구절(그대로). 요약·의역 금지


class PersonaProfile(BaseModel):
    """개인화 '조합' 레이어 산출물 — 완성된 페르소나에 맞춰 리소스를 한 번에 조합.

    scoring(weights_for)·narrator(profile_for)가 각자 집던 것을 여기서 합쳐 한 산출물로.
    화면 '개인화 프로필 카드'로 노출(왜 이렇게 추천하는지의 근거 요약).
    """

    segment: str  # 세그먼트 라벨
    headline: str  # 한 줄 요약 ("통근을 가장 중시하는 1인 가구")
    workplace: Optional[str] = None  # 대표 직장(통근 발품 기준, 가정)
    weights: dict  # 스코어 가중치 (반영 후 = after)
    baseWeights: dict = {}  # 가구 기본 가중치 (반영 전 = before) — 화면 before→after 대비(B4)
    weightBasis: str  # 가중치 출처 한 줄
    consumption: list[str]  # 소비 성향(카드통계 근거)
    consumptionSignals: list[dict] = []  # 성향 신호 + 출처(세그먼트/실측/진술) — 증거 위계 노출
    resources: list[str]  # 조합된 리소스(발품에 등장할 것들)
    budgetBand: str  # 예산 밴드 설명


# ── 지출 분석 + 만기 결정 리포트 ────────────────────────────────────
class SpendAnalysis(BaseModel):
    """개인 지출 집계(합성 마이데이터, 가드레일 T2SQL/표준쿼리). ⚠️ compare에 유입 금지 — 리포트 맥락만."""

    monthlyTotal: int  # 월평균 총지출
    fixedMonthly: int  # 월평균 고정지출
    variableMonthly: int  # 월평균 변동지출(여력)
    topCategories: list[dict]  # [{category, monthly}]
    trend: list[dict]  # [{month, total}]
    dynamicQueries: list[dict] = []  # LLM 동적 질문/SQL/결과/폴백여부
    synthetic: bool = True  # 합성 시연 데이터


class NextAction(BaseModel):
    """⑥ 다음 액션 — 자격 기반 정책대출 차액(버팀목/디딤돌). 상담 예약의 구체적 이유 제공."""

    headline: str  # "버팀목 청년 전세대출 자격이면 이자를 아껴요"
    detail: str  # 근거 한 줄(적용 금리·비교 대상)
    annualSaving: int = 0  # 연 이자 절감액(원). 0=자격 미해당(요건 확인 안내)
    eligible: bool = False


class DecisionReport(BaseModel):
    """만기 결정 리포트 — 최종 산출물. ①상황 ②채점 ③동네 ④하루 ⑤지출 실현가능성 ⑥액션."""

    persona: "PersonaProfile"
    clarify: Optional["ClarifyResult"] = None  # ① HITL 반영 내역
    comparison: "CompareResponse"  # ② 3갈래 (compare 출력, 읽기전용)
    selectedBranch: Branch
    topRegion: Optional["Region"] = None  # ③④ 동네·발품
    dayBrief: str = ""  # ④ 발품 핵심
    spend: Optional[SpendAnalysis] = None  # ⑤ (없으면 리포트는 ①~④+⑥로 완성)
    feasibility: str = ""  # ⑤ 정보형 문장
    nextAction: Optional["NextAction"] = None  # ⑥ 자격 기반 차액(버팀목/디딤돌)
    dday: int
    noticeDeadline: str


# ── 하루 시뮬레이션 ─────────────────────────────────────────────────
class Scene(BaseModel):
    time: str
    emoji: str
    visual: str
    caption1: str
    caption2: str
    basis: Optional[str] = None


class SimulateResponse(BaseModel):
    scenes: list[Scene]
    monthlyCost: int


# ── 상품 ────────────────────────────────────────────────────────────
class Product(BaseModel):
    name: str
    condition: str
    recommendReason: str
    monthlyPayment: Optional[int] = None
    maxAmount: Optional[int] = None
    basis: str


class ProductsResponse(BaseModel):
    branch: Branch
    mainLoan: Product
    guarantee: Optional[Product] = None
    extra: Optional[Product] = None


# ── 예약 ────────────────────────────────────────────────────────────
class ReservationRequest(BaseModel):
    branch: Branch
    date: str
    productName: str


class ReservationResponse(BaseModel):
    ok: bool
    id: int


# ── 브리핑 (LLM) ────────────────────────────────────────────────────
class BriefingRequest(BaseModel):
    kind: BriefingKind
    context: dict


class BriefingResponse(BaseModel):
    text: str


# ── 통보 문자 초안 (LLM) ────────────────────────────────────────────
class DraftNoticeRequest(BaseModel):
    expiryDate: str
    address: Optional[str] = None


class DraftNoticeResponse(BaseModel):
    draft: str


# ── 엔드포인트 요청 래퍼 (types.ts엔 없지만 client.ts가 보내는 body) ──
class CompareRequest(BaseModel):
    contract: ContractInfo
    finance: FinanceInfo


class SimulateRequest(BaseModel):
    branch: Branch
    regionId: str


class ClarifyRequest(BaseModel):
    contract: ContractInfo
    finance: FinanceInfo
    priorNotes: list[str] = []  # 이미 반영·확정한 자유입력들(모순 되묻기용)
    householdSelected: bool = True  # 가구 유형을 실제 선택했는지(False=문진 초반 미선택 → 가구 상충 스킵, J1)


class ValidateProfileRequest(BaseModel):
    """SC-14 최종 프로필 종합검증 요청 — 누적 자유입력 전체 + 가구 + 예산을 한 번에 검증."""

    contract: ContractInfo
    finance: FinanceInfo
    budget: int = 0  # 참고 예산(고른 갈래 depositOrPrice 등) — 예산↔선호 상충 판단 맥락
    householdSelected: bool = True
    acceptedPairs: list[list[str]] = []  # 사용자가 '둘 다 맞아요'로 확인한 신호 쌍 — 재검증 시 제외(K1)


class ReportRequest(BaseModel):
    contract: ContractInfo
    finance: FinanceInfo
    branch: Branch
    personaId: Optional[str] = None  # 'P1'|'P2'|'P3' (합성 마이데이터). 없으면 가구/계약에서 추론
    regionId: Optional[str] = None


class HitlRequest(BaseModel):
    """HITL 확정 이벤트(관측 전용) — '제안은 AI, 확정은 사람'을 Langfuse 세션에 남긴다. types.ts 계약 아님."""

    choice: Literal["applied", "skipped"]
    signals: list[str] = []  # 제안됐던 조정(자유입력 신호)
    note: str = ""


class ProductsRequest(BaseModel):
    branch: Branch
    # comparison은 향후 확장용(Optional). contract는 이사 갈래 전세/월세 상품 분기용(2026-07-30 추가).
    comparison: Optional[CompareResponse] = None
    contract: Optional[ContractInfo] = None


class AnalyzeResponse(BaseModel):
    """분석 에이전트(intake→clarify→compare→route→persona→narrate) 결과.

    계산(comparison) + 명확화(clarify) + 개인화 조합(persona) + 통역(briefing)을 한 번에.
    clarify/persona는 하위호환 위해 Optional.
    """

    comparison: CompareResponse
    briefing: str
    clarify: Optional[ClarifyResult] = None
    persona: Optional[PersonaProfile] = None
