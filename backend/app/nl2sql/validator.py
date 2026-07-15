"""LLM이 생성한 SQL을 실행 전에 반드시 통과시켜야 하는 안전장치.

검증 순서: (1) SELECT-only, (2) 위험 키워드 부재, (3) 화이트리스트 테이블만
참조. 이 세 가지를 모두 통과한 SQL만 executor.py로 넘어간다.

한계(1단계 스캐폴딩 수준): 테이블명 추출은 정규식 기반 best-effort이며,
서브쿼리/CTE 등 복잡한 SQL은 다음 단계에서 SQL 파서 도입을 검토해야 한다.
"""
import re

FORBIDDEN_KEYWORDS = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "MERGE",
    "CREATE",
    "GRANT",
    "REVOKE",
    "EXEC",
    "EXECUTE",
    "CALL",
)

_TABLE_REF_RE = re.compile(r"(?:FROM|JOIN)\s+([A-Za-z_][A-Za-z0-9_]*)", re.IGNORECASE)


class SQLValidationError(Exception):
    """생성된 SQL이 안전 검증을 통과하지 못했을 때 발생한다."""


def validate_sql(sql: str, allowed_tables: set[str]) -> str:
    """검증을 통과하면 정리된 SQL 문자열을 그대로 반환하고, 아니면 예외를 던진다."""
    cleaned = sql.strip()
    if not cleaned:
        raise SQLValidationError("빈 SQL은 실행할 수 없습니다.")

    # 세미콜론으로 구분된 다중 statement 금지
    body = cleaned[:-1] if cleaned.endswith(";") else cleaned
    if ";" in body:
        raise SQLValidationError("다중 statement는 허용되지 않습니다.")

    if not re.match(r"^\s*SELECT\b", cleaned, re.IGNORECASE):
        raise SQLValidationError("SELECT문만 허용됩니다.")

    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{keyword}\b", cleaned, re.IGNORECASE):
            raise SQLValidationError(f"허용되지 않는 키워드가 포함되어 있습니다: {keyword}")

    referenced_tables = {match.lower() for match in _TABLE_REF_RE.findall(cleaned)}
    if not referenced_tables:
        raise SQLValidationError("조회 대상 테이블을 확인할 수 없습니다.")

    unknown_tables = referenced_tables - {t.lower() for t in allowed_tables}
    if unknown_tables:
        raise SQLValidationError(f"화이트리스트에 없는 테이블입니다: {', '.join(sorted(unknown_tables))}")

    return cleaned
