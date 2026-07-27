"""가드레일 걸린 Text-to-SQL — 개인 지출 분석 전용.

설계 논리: 규정·시세 조회는 질문이 고정 → 결정론 쿼리. **개인 지출 분석은 질문이 사람마다 다르다**
(재택 1인=배달·구독 / 신혼=주거 여력 / 자녀=교육비) → 페르소나가 질문을 정하므로 쿼리가 동적일 정당성.
여기에만 통제된 생성을 허용한다. "고정 질문엔 결정론, 동적 질문엔 통제된 생성."

⚠️ 철칙: 지출 분석 결과는 **compare(예산 계산)에 절대 유입 금지.** 리포트의 맥락 정보로만.

가드레일 7종(전부 필수):
 1) SELECT만 (파서+authorizer로 쓰기·DDL·PRAGMA·ATTACH 차단, 다중문 차단)
 2) 테이블 화이트리스트: transactions 1개
 3) 컬럼 화이트리스트: 스키마 7개 컬럼
 4) persona_id 슬롯: WHERE persona_id=:pid 바인딩 필수(타 페르소나 차단)
 5) 결과 검증: 행 상한 1000, 집계 음수 이상치 → 폴백
 6) 실패 폴백: 표준 쿼리 5종
 7) Langfuse 기록: 질문·SQL·검증·폴백

LLM off 모드: 표준 쿼리 5종만으로 동일 리포트(오프라인 완주).
"""

import json
import re
import sqlite3
from typing import Optional

from ..core.config import BACKEND_ROOT, settings
from ..core.llm import generate
from ..core.tracing import trace_event

MYDATA_DB = BACKEND_ROOT / "data" / "mydata.demo.db"

ALLOWED_TABLE = "transactions"
ALLOWED_COLUMNS = {"tx_id", "persona_id", "tx_date", "category", "merchant_label", "amount", "is_fixed"}
ALLOWED_FUNCTIONS = {"count", "sum", "avg", "min", "max", "round", "abs", "substr", "total"}

# sqlite authorizer 액션/반환 코드(안정값 — 버전 무관 하드코딩)
_SQLITE_OK, _SQLITE_DENY = 0, 1
_SQLITE_SELECT, _SQLITE_READ, _SQLITE_FUNCTION = 21, 20, 31

_BANNED = ("insert", "update", "delete", "drop", "alter", "attach", "detach", "pragma", "create", "replace", "vacuum")


class GuardrailError(Exception):
    """가드레일 차단 — 호출부가 폴백으로 대체."""


def _authorizer(action, arg1, arg2, dbname, trigger):
    """구조적 가드레일 — SELECT/READ(화이트리스트 테이블·컬럼)/허용함수만. 그 외 전부 DENY."""
    if action == _SQLITE_SELECT:
        return _SQLITE_OK
    if action == _SQLITE_READ:
        table, col = arg1, arg2
        if table != ALLOWED_TABLE:
            return _SQLITE_DENY
        if col and col not in ALLOWED_COLUMNS:
            return _SQLITE_DENY
        return _SQLITE_OK
    if action == _SQLITE_FUNCTION:
        return _SQLITE_OK if (arg2 or "").lower() in ALLOWED_FUNCTIONS else _SQLITE_DENY
    return _SQLITE_DENY  # 쓰기·DDL·PRAGMA·ATTACH 등


def _validate_sql_text(sql: str) -> None:
    """텍스트 레벨 가드레일(파서) — 다중문·비SELECT·금지키워드·persona_id 슬롯."""
    s = (sql or "").strip().rstrip(";").strip()
    if ";" in s:
        raise GuardrailError("다중 문장 금지")
    if not re.match(r"(?is)^select\b", s):
        raise GuardrailError("SELECT만 허용")
    low = s.lower()
    for bad in _BANNED:
        if re.search(rf"\b{bad}\b", low):
            raise GuardrailError(f"금지 키워드: {bad}")
    if not re.search(r"persona_id\s*=\s*:pid", low):
        raise GuardrailError("persona_id=:pid 바인딩 필수")


def guarded_execute(sql: str, persona_id: str, *, db_path: Optional[str] = None) -> list:
    """검증 통과한 SELECT만 실행. persona_id는 :pid로 바인딩(타 페르소나 차단). 위반/실패 → GuardrailError."""
    _validate_sql_text(sql)  # 가드레일 1·4
    path = db_path or (str(MYDATA_DB) if MYDATA_DB.exists() else None)
    if not path:
        raise GuardrailError("mydata DB 없음 (scripts/gen_mydata.py)")
    conn = None
    try:
        conn = sqlite3.connect(path)
        conn.set_authorizer(_authorizer)  # 가드레일 1·2·3
        cur = conn.execute(sql, {"pid": persona_id})
        rows = cur.fetchmany(1001)
        if len(rows) > 1000:  # 가드레일 5
            raise GuardrailError("행 상한 초과")
        return rows
    except sqlite3.Error as e:  # authorizer denial·연결/실행 실패 등 → 차단
        raise GuardrailError(f"실행 차단: {e}")
    finally:
        if conn is not None:
            conn.close()


# ── 표준 쿼리 5종 (결정론 폴백 = LLM off 경로) ────────────────────────
def _std_scalar(sql: str, pid: str, db_path: Optional[str]) -> int:
    rows = guarded_execute(sql, pid, db_path=db_path)
    return int((rows[0][0] if rows and rows[0] else 0) or 0)


def standard_aggregates(persona_id: str, *, db_path: Optional[str] = None) -> dict:
    """표준 5종: 월평균 총지출/고정/변동 + 카테고리 top3 + 3개월 추이. (3개월 스냅샷 → /3)"""
    total = _std_scalar("SELECT SUM(amount)/3 FROM transactions WHERE persona_id=:pid", persona_id, db_path)
    fixed = _std_scalar(
        "SELECT SUM(amount)/3 FROM transactions WHERE persona_id=:pid AND is_fixed=1", persona_id, db_path
    )
    variable = _std_scalar(
        "SELECT SUM(amount)/3 FROM transactions WHERE persona_id=:pid AND is_fixed=0", persona_id, db_path
    )
    top = guarded_execute(
        "SELECT category, SUM(amount)/3 FROM transactions WHERE persona_id=:pid "
        "GROUP BY category ORDER BY SUM(amount) DESC LIMIT 3",
        persona_id,
        db_path=db_path,
    )
    trend = guarded_execute(
        "SELECT substr(tx_date,1,7), SUM(amount) FROM transactions WHERE persona_id=:pid "
        "GROUP BY substr(tx_date,1,7) ORDER BY substr(tx_date,1,7)",
        persona_id,
        db_path=db_path,
    )
    return {
        "monthlyTotal": total,
        "fixedMonthly": fixed,
        "variableMonthly": variable,
        "topCategories": [{"category": c, "monthly": int(a or 0)} for c, a in top],
        "trend": [{"month": m, "total": int(t or 0)} for m, t in trend],
    }


# ── LLM 동적 질문/SQL 생성 (통제된 생성) ──────────────────────────────
_Q_SYSTEM = (
    "너는 개인 지출 분석 보조다. 아래 사용자 맥락에서 '이 사람의 주거 갈래 결정에 유의미한 "
    "지출 질문'을 1~3개 만든다. 반드시 transactions 스키마(persona_id, tx_date, category, amount, is_fixed) "
    '안에서 답할 수 있는 질문만. 출력은 오직 JSON 배열: ["질문1", ...]'
)
_SQL_SYSTEM = (
    "너는 SQLite 쿼리 생성기다. transactions(persona_id, tx_date, category, merchant_label, amount, is_fixed) "
    "테이블만, SELECT만, WHERE에 반드시 `persona_id = :pid` 를 포함한다. 다른 테이블·컬럼·쓰기·세미콜론 금지. "
    "질문에 대한 집계 SELECT 하나만 출력(설명 없이 SQL만)."
)


def _llm_questions(persona_ctx: str, branch: str) -> list[str]:
    raw = generate(system=_Q_SYSTEM, user=f"맥락: {persona_ctx}\n선택 갈래: {branch}", fallback=lambda: "")
    m = re.search(r"\[.*\]", raw or "", re.DOTALL)
    if not m:
        return []
    try:
        arr = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    return [str(x) for x in arr][:3] if isinstance(arr, list) else []


def _llm_sql(question: str) -> Optional[str]:
    raw = generate(system=_SQL_SYSTEM, user=f"질문: {question}\nSQL:", fallback=lambda: "")
    m = re.search(r"(?is)\bselect\b.*", raw or "")
    return m.group(0).strip().rstrip(";") if m else None


# ── 최종 분석 ────────────────────────────────────────────────────────
def analyze_spending(
    persona_id: str, *, persona_ctx: Optional[str] = None, branch: str = "", db_path: Optional[str] = None
) -> Optional[dict]:
    """지출 집계(표준 5종) + (llm_active 시) 동적 질문/SQL. mydata 없으면 None(리포트는 ①~④+⑥로 완성)."""
    if not (db_path or MYDATA_DB.exists()):
        return None
    std = standard_aggregates(persona_id, db_path=db_path)
    dynamic: list[dict] = []
    if settings.llm_active and persona_ctx:
        for q in _llm_questions(persona_ctx, branch):
            entry = {"question": q, "sql": None, "result": None, "fellBack": False}
            try:
                sql = _llm_sql(q)
                if not sql:
                    raise GuardrailError("SQL 생성 실패")
                entry["sql"] = sql
                rows = guarded_execute(sql, persona_id, db_path=db_path)
                val = rows[0][0] if rows and rows[0] else None
                if isinstance(val, (int, float)) and val < 0:  # 가드레일 5
                    raise GuardrailError("음수 이상치")
                entry["result"] = int(val) if isinstance(val, (int, float)) else val
            except GuardrailError as e:
                entry["fellBack"] = True
                entry["blockReason"] = str(e)
                entry["result"] = std["variableMonthly"]  # 가드레일 6: 표준 집계로 대체
            trace_event(  # 가드레일 7
                "spend_query",
                metadata={
                    "question": entry["question"],
                    "sql": entry["sql"],
                    "fell_back": entry["fellBack"],
                    "block_reason": entry.get("blockReason"),
                },
            )
            dynamic.append(entry)
    return {**std, "dynamicQueries": dynamic, "synthetic": True}
