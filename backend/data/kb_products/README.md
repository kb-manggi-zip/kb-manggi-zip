# KB 상품 RAG 소스 (Phase B4)

`agents/matcher.py` 가 이 폴더의 `*.md` 를 임베딩(FAISS)해 갈래별 상품 top3 + 사유를 만든다.

## 채워 넣는 규칙 (사람이 할 일)
- 공시 페이지 기준으로 상품 5~8건 정리 (전세대출 연장/증액, 청년·신혼 전세대출, 디딤돌, 반환보증, 화재보험, 청약 등)
- 각 파일 상단에 `source_url:` 과 `checked_at:` 명시
- 숫자(한도·금리·요율)는 **문서 원문 그대로** — matcher는 이 원문만 인용한다 (지어내기 금지)

파일당 상품 1개 권장. 예: `jeonse_extend.md`, `didimdol.md`, `return_guarantee.md` ...
