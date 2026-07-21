"""LangGraph 오케스트레이션 — Phase B3 SEAM (미구현·미연결).

현재 라우터(routers/api.py)는 tools·agents 를 **직접** 호출한다 (단순·안정).
Phase B3에서 이 파일에 Supervisor 그래프를 구성하고, 라우터가 그래프를 경유하도록 바꾼다.
그래프로 바꿔도 각 노드의 결과(계산·집계·통역)는 지금과 동일해야 한다(회귀 기준).

의도한 그래프 (기획서 7절):
    Supervisor
      ├─ intake        (문진 정리)
      ├─ compare       → tools/compare.py           (LLM 없음)
      ├─ regions       → tools/molit.py             (LLM 없음)
      ├─ simulate      → agents/narrator.py         (LLM)
      ├─ content       → agents/briefing.py         (LLM, SSE)
      └─ finance       → agents/matcher.py (RAG)    (LLM)
    renewal 선택 시 regions/simulate 스킵 → finance 직행.

구현 시:
  - requirements.txt 의 langgraph·langfuse 주석 해제
  - 상태 스키마 = app/schemas.py 재사용 (AppState 확장)
  - Langfuse 트레이싱을 전 노드에 부착 (발표용 노드 경로 캡처)
"""

# STUB: Phase B3 — LangGraph Supervisor + Langfuse.
# from langgraph.graph import StateGraph  # (langgraph 설치 후)
#
# def build_graph():
#     ...  # 노드 등록 + 엣지 + 조건분기(renewal → finance)
#     return graph.compile()


def build_graph():  # pragma: no cover
    raise NotImplementedError(
        "LangGraph 오케스트레이션은 Phase B3에서 구현합니다. "
        "현재는 routers/api.py 가 tools·agents 를 직접 호출합니다."
    )
