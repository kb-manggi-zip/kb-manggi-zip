"""동네 후보 폴백 데이터 — 프론트 src/data/regions.ts 이식.

Phase B2에서 tools/molit.py(실거래) + tools/kbland.py(KB 통계)가
이 shape(Region)을 그대로 채운다. 그전까지 엔드포인트는 이 fixture로 동작.
"""
from ..schemas import Region

REGIONS_BUY: list[Region] = [
    Region(id="mapo", name="마포구 합정동", midPrice=530_000_000, surplus=24_000_000,
           tradeCount=38, tags=["역세권", "카페거리"], lat=37.5498, lng=126.9137, branch="매매"),
    Region(id="eunpyeong", name="은평구 녹번동", midPrice=490_000_000, surplus=64_000_000,
           tradeCount=52, tags=["조용한", "학교 밀집"], lat=37.6059, lng=126.9286, branch="매매"),
    Region(id="dobong", name="도봉구 창동", midPrice=430_000_000, surplus=124_000_000,
           tradeCount=71, tags=["자연친화", "지하철 직통"], lat=37.6533, lng=127.0473, branch="매매"),
]

REGIONS_MOVE: list[Region] = [
    Region(id="seongbuk", name="성북구 길음동", midPrice=290_000_000, surplus=18_000_000,
           tradeCount=44, tags=["학원가", "마트 가깝"], lat=37.6038, lng=127.0193, branch="이사"),
    Region(id="nowon", name="노원구 상계동", midPrice=260_000_000, surplus=48_000_000,
           tradeCount=66, tags=["공원 인접", "대형마트"], lat=37.6550, lng=127.0631, branch="이사"),
    Region(id="jungnang", name="중랑구 면목동", midPrice=230_000_000, surplus=78_000_000,
           tradeCount=55, tags=["조용한 주택가", "경전철"], lat=37.5780, lng=127.0924, branch="이사"),
]

REGIONS_MONTHLY: list[Region] = [
    Region(id="mapo-m", name="마포구 망원동", midPrice=72_000_000, monthlyMidPrice=1_950_000,
           surplus=50_000, tradeCount=29, tags=["한강공원", "힙한거리"], lat=37.5561, lng=126.9026, branch="이사"),
    Region(id="seodaemun-m", name="서대문구 홍제동", midPrice=60_000_000, monthlyMidPrice=1_800_000,
           surplus=200_000, tradeCount=37, tags=["산책로", "재래시장"], lat=37.5893, lng=126.9392, branch="이사"),
    Region(id="seongbuk-m", name="성북구 보문동", midPrice=55_000_000, monthlyMidPrice=1_700_000,
           surplus=300_000, tradeCount=41, tags=["카페거리", "대학가"], lat=37.5893, lng=127.0192, branch="이사"),
]
