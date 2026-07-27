"""합성 마이데이터 생성 — data/mydata.demo.db (transactions 1테이블).

⚠️ 전부 **합성 시연 데이터**다. 실측 아님. 화면·문서에서 "합성 예시"로 명시한다.
   실서비스는 신용정보원 마이데이터 표준 규격 수신 → 이 분석 테이블로 정규화하는 어댑터 계층을 둔다
   (분석 로직·가드레일은 그대로). 여기선 리포트 ⑤("지출 구조로 실현 가능한가")에 필요한 최소 1테이블만.

카테고리 비중 근거: agents/spending_profiles.yaml(카드통계 도출값)과 정합하게 설계 — 임의 분포 아님.
  P1(1인·재택): 배달·카페·구독·여가 높음   P2(신혼): 마트·주거·쇼핑   P3(직장인): 교통·외식 높음
결정론(seed 고정) → 재실행해도 동일 스냅샷.

실행: PYTHONPATH=. python scripts/gen_mydata.py
"""

import random
import sqlite3
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = BACKEND_ROOT / "data" / "mydata.demo.db"
MONTHS = ["202605", "202606", "202607"]  # 최근 3개월(합성)

SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    tx_id         INTEGER PRIMARY KEY,
    persona_id    TEXT NOT NULL,
    tx_date       TEXT NOT NULL,       -- 'YYYY-MM-DD'
    category      TEXT NOT NULL,       -- 식비/카페/배달/구독/교통/주거/보험/쇼핑/교육/기타
    merchant_label TEXT,
    amount        INTEGER NOT NULL,    -- 원(지출 양수)
    is_fixed      INTEGER NOT NULL     -- 1=고정지출, 0=변동
);
"""

# 고정지출 카테고리(정기 이체·구독·보험·교통정기·주거)
FIXED = {"주거", "보험", "구독"}

# 페르소나별 월 카테고리 예산(원). 소득 대비 상식선 + 프로필 비중 반영.
#   (category, monthly_won, is_fixed, [merchant 후보])
PROFILES = {
    # P1 1인·재택 (소득 4.5천 → 월지출 ~191만). 배달·카페·구독·여가↑, 통근 적음.
    "P1": [
        ("주거", 700_000, 1, ["월세 이체", "관리비"]),
        ("식비", 250_000, 0, ["동네마트", "편의점", "김밥천국"]),
        ("카페", 120_000, 0, ["스타벅스", "메가커피", "투썸"]),
        ("배달", 200_000, 0, ["배달의민족", "쿠팡이츠", "요기요"]),
        ("구독", 50_000, 1, ["넷플릭스", "유튜브프리미엄", "멜론"]),
        ("교통", 80_000, 1, ["교통카드 충전"]),
        ("보험", 60_000, 1, ["실손보험"]),
        ("쇼핑", 250_000, 0, ["쿠팡", "무신사", "올리브영"]),
        ("기타", 200_000, 0, ["헬스장", "PC방", "노래방", "취미"]),
    ],
    # P2 신혼 (소득 7천 → 월지출 ~300만). 마트·주거·쇼핑(인터넷)·나들이↑, 유아 준비 시작.
    "P2": [
        ("주거", 950_000, 1, ["전세대출 이자", "관리비"]),
        ("식비", 500_000, 0, ["이마트", "홈플러스", "정육점"]),
        ("카페", 80_000, 0, ["스타벅스", "폴바셋"]),
        ("배달", 100_000, 0, ["배달의민족", "쿠팡이츠"]),
        ("구독", 40_000, 1, ["넷플릭스", "디즈니+"]),
        ("교통", 100_000, 1, ["교통카드 충전", "주유"]),
        ("보험", 120_000, 1, ["종합보험", "실손보험"]),
        ("쇼핑", 500_000, 0, ["쿠팡", "마켓컬리", "이케아"]),
        ("교육", 100_000, 0, ["문화센터", "육아용품"]),
        ("기타", 250_000, 0, ["주말 나들이", "숙박", "외식"]),
    ],
    # P3 월세 직장인 (소득 5.5천 → 월지출 ~228만). 교통·외식↑.
    "P3": [
        ("주거", 750_000, 1, ["월세 이체", "관리비"]),
        ("식비", 300_000, 0, ["회사 근처 식당", "편의점", "마트"]),
        ("카페", 100_000, 0, ["스타벅스", "이디야"]),
        ("배달", 120_000, 0, ["배달의민족", "요기요"]),
        ("구독", 40_000, 1, ["넷플릭스", "웨이브"]),
        ("교통", 150_000, 1, ["교통카드 충전", "택시", "KTX"]),
        ("보험", 70_000, 1, ["실손보험"]),
        ("쇼핑", 200_000, 0, ["쿠팡", "무신사"]),
        ("기타", 350_000, 0, ["회식", "모임", "외식"]),
    ],
}


def _gen_txns(persona_id: str, spec: list, rnd: random.Random) -> list[tuple]:
    rows = []
    for ym in MONTHS:
        y, m = int(ym[:4]), int(ym[4:])
        for category, monthly, is_fixed, merchants in spec:
            # 고정지출은 월 1건(정기), 변동은 3~7건으로 분할
            n = 1 if is_fixed else rnd.randint(3, 7)
            # 월 총액을 n건으로 분배(±15% 지터, 합은 monthly 유지)
            weights = [rnd.uniform(0.85, 1.15) for _ in range(n)]
            s = sum(weights)
            for i in range(n):
                amt = int(monthly * weights[i] / s)
                if amt <= 0:
                    continue
                day = rnd.randint(1, 28)
                rows.append(
                    (
                        persona_id,
                        f"{y}-{m:02d}-{day:02d}",
                        category,
                        rnd.choice(merchants),
                        amt,
                        is_fixed,
                    )
                )
    return rows


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    rnd = random.Random(20260727)  # 결정론
    all_rows: list[tuple] = []
    for pid, spec in PROFILES.items():
        all_rows.extend(_gen_txns(pid, spec, rnd))
    conn.executemany(
        "INSERT INTO transactions(persona_id, tx_date, category, merchant_label, amount, is_fixed) "
        "VALUES (?,?,?,?,?,?)",
        all_rows,
    )
    conn.commit()
    # 요약 출력(검증용)
    for pid in PROFILES:
        tot = conn.execute("SELECT SUM(amount) FROM transactions WHERE persona_id=?", (pid,)).fetchone()[0]
        n = conn.execute("SELECT COUNT(*) FROM transactions WHERE persona_id=?", (pid,)).fetchone()[0]
        print(f"{pid}: {n}건, 3개월 합 {tot:,}원 (월평균 {tot // 3:,}원)")
    conn.close()
    print(f"→ {DB_PATH}")


if __name__ == "__main__":
    main()
