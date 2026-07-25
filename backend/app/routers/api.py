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

import asyncio

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from ..agents import briefing, drafter, matcher, narrator
from ..core.db import get_db
from ..graph import build_compare_graph, build_regions_graph
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

router = APIRouter(prefix="/api")

_compare_graph = build_compare_graph()


@router.post("/compare", response_model=CompareResponse)
def compare(req: CompareRequest) -> CompareResponse:
    result = _compare_graph.invoke(
        {
            "contract": req.contract.model_dump(),
            "finance": req.finance.model_dump(),
        }
    )
    return CompareResponse(**result["comparison"])


_regions_graph = build_regions_graph()


@router.get("/regions", response_model=list[Region])
def regions(branch: str = Query(...), budget: int = 0) -> list[Region]:
    result = _regions_graph.invoke({"branch": branch, "budget": budget})
    return result["regions"]


@router.post("/simulate", response_model=SimulateResponse)
def simulate(req: SimulateRequest) -> SimulateResponse:
    return narrator.run(req.branch, req.regionId)


@router.post("/products", response_model=ProductsResponse)
def products(req: ProductsRequest) -> ProductsResponse:
    return matcher.run(req.branch, req.comparison)


@router.post("/briefing", response_model=BriefingResponse)
def briefing_endpoint(req: BriefingRequest) -> BriefingResponse:
    # 한 번에 반환(비스트리밍). 타이핑 UX는 /briefing/stream 사용.
    return BriefingResponse(text=briefing.run(req))


@router.post("/briefing/stream")
async def briefing_stream(req: BriefingRequest) -> EventSourceResponse:
    """통역 문장을 토큰 단위로 SSE 스트리밍 (프론트 타이핑 효과와 연결).

    이벤트: data:<청크> 반복 → 마지막에 event:done. LLM 비활성 시 폴백 템플릿을 어절로 흘림.
    """

    async def event_gen():
        for chunk in briefing.stream(req):
            yield {"data": chunk}
            await asyncio.sleep(0.03)  # 청크 페이싱 — 폴백도 '타이핑'처럼 보이게 (실 Claude는 자연 페이스)
        yield {"event": "done", "data": "[DONE]"}

    return EventSourceResponse(event_gen())


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
