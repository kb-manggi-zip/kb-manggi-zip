"""통보 문자 초안 에이전트 — 갱신 통보 문자 (LLM seam).

client.ts 로컬 draftNotice 템플릿을 폴백으로 이식.
[동·호수] placeholder 유지, 법적 확언 금지.
"""

from datetime import date

from ..core.llm import generate
from ..schemas import DraftNoticeRequest, DraftNoticeResponse


def _format_korean_date(iso: str | None) -> str:
    if not iso:
        return "[만기일]"
    try:
        d = date.fromisoformat(iso[:10])
        return f"{d.year}년 {d.month}월 {d.day}일"
    except ValueError:
        return "[만기일]"


def _template(req: DraftNoticeRequest) -> str:
    expiry = _format_korean_date(req.expiryDate)
    addr = req.address or "[동·호수]"
    return (
        f"안녕하세요, {addr}에 거주 중인 임차인입니다.\n\n"
        f"{expiry}자로 계약이 만료되어, 주택임대차보호법에 따른 계약갱신을 요청드리고자 연락드립니다.\n\n"
        "조건 협의가 필요하시면 편하신 시간에 말씀 부탁드립니다.\n\n"
        "감사합니다."
    )


def run(req: DraftNoticeRequest) -> DraftNoticeResponse:
    draft = generate(
        system="계약갱신 의사 통보 문자 초안을 정중하게 작성한다. 법적 확언·협박·권유 금지. "
        "빠진 정보는 [대괄호] placeholder로 남긴다.",
        user=f"만기일={req.expiryDate} 주소={req.address}",
        fallback=lambda: _template(req),
    )
    return DraftNoticeResponse(draft=draft)
