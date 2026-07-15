"""검증된 SQL만 Oracle에 실행한다. validator를 우회하는 호출 경로를 만들지 않는다."""
from app.nl2sql.catalog import allowed_tables
from app.nl2sql.validator import validate_sql
from app.repositories.catalog_query_repo import run_select


def execute_query(sql: str) -> list[dict]:
    validated_sql = validate_sql(sql, allowed_tables())
    return run_select(validated_sql)
