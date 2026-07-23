"""API 라우터 — 엔드포인트 계약(types.ts 1:1).

| 엔드포인트            | 처리                              | LLM |
|----------------------|-----------------------------------|-----|
| POST /api/compare    | tools.compare (3종+보증료)        | ❌  |
| GET  /api/regions    | tools.molit 필터 → Region[]       | ❌  |
| POST /api/simulate   | agents.narrator → SimulateResponse| ✅* |
| POST /api/products   | agents.matcher → ProductsResponse | ✅* |
| POST /api/briefing   | agents.briefing → 통역 문장       | ✅* |
| POST /api/draft-notice | agents.drafter                  | ✅* |
| POST /api/reservation| DB 저장                           | ❌  |
(*: 현재 LLM 비활성 시 템플릿/fixture 폴백)
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..agents import briefing, drafter, matcher, narrator
from ..core.db import get_db
from ..models.reservation import Reservation
from ..schemas import (
    BriefingRequest,
    BriefingResponse,
    CompareRequest,
    CompareResponse,
    DraftNoticeRequest,
    DraftNoticeResponse,
    ProductsRequest,
    ProductsResponse,
    Region,
    ReservationRequest,
    ReservationResponse,
    SimulateRequest,
    SimulateResponse,
)
from ..tools import molit
from ..tools.compare import compute_compare
from ..graph import build_graph
router = APIRouter(prefix="/api")


_compiled_graph = build_graph()

@router.post("/compare", response_model=CompareResponse)
def compare(req: CompareRequest) -> CompareResponse:
    result = _compiled_graph.invoke({
        "contract": req.contract.model_dump(),
        "finance": req.finance.model_dump(),
    })
    return CompareResponse(**result["comparison"])


@router.get("/regions", response_model=list[Region])
def regions(branch: str = Query(...), budget: int = 0) -> list[Region]:
    # branch: '매매' | '이사' | '이사-월세'(client.ts regionsMonthly)
    return molit.regions_by_branch(branch, budget)


@router.post("/simulate", response_model=SimulateResponse)
def simulate(req: SimulateRequest) -> SimulateResponse:
    return narrator.run(req.branch, req.regionId)


@router.post("/products", response_model=ProductsResponse)
def products(req: ProductsRequest) -> ProductsResponse:
    return matcher.run(req.branch, req.comparison)


@router.post("/briefing", response_model=BriefingResponse)
def briefing_endpoint(req: BriefingRequest) -> BriefingResponse:
    # STUB: Phase B4에서 SSE 스트리밍(sse-starlette)으로 전환.
    return BriefingResponse(text=briefing.run(req))


@router.post("/draft-notice", response_model=DraftNoticeResponse)
def draft_notice(req: DraftNoticeRequest) -> DraftNoticeResponse:
    return drafter.run(req)


@router.post("/reservation", response_model=ReservationResponse)
def reservation(req: ReservationRequest, db: Session = Depends(get_db)) -> ReservationResponse:
    row = Reservation(branch=req.branch, date=req.date, product_name=req.productName)
    db.add(row)
    db.commit()
    db.refresh(row)
    return ReservationResponse(ok=True, id=row.id)
