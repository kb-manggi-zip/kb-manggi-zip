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

from typing import Literal, Optional

from pydantic import BaseModel

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


class ProductsRequest(BaseModel):
    branch: Branch
    # client.ts는 {branch}만 보냄. comparison은 향후 확장용(Optional).
    comparison: Optional[CompareResponse] = None


class AnalyzeResponse(BaseModel):
    """분석 에이전트(intake→compare→narrate) 결과 — 계산 + 개인화 통역을 한 번에."""

    comparison: CompareResponse
    briefing: str
