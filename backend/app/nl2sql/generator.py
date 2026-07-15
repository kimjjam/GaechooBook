"""LLM에 자연어 질문 → SQL 생성을 요청한다.

여기서 나온 SQL은 그대로 신뢰하지 않는다 — nl2sql/validator.py를 반드시
거친 뒤에만 executor.py에서 실행된다.
"""
import re

from app.api_clients.llm_client import get_llm_client
from app.nl2sql.catalog import CATALOG

_CODE_FENCE_RE = re.compile(r"```(?:sql)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)


def _build_prompt(question: str) -> str:
    schema_lines = []
    for table, meta in CATALOG.items():
        columns = ", ".join(f"{col}({desc})" for col, desc in meta["columns"].items())
        schema_lines.append(f"- {table}({meta['description']}): {columns}")
    schema_desc = "\n".join(schema_lines)

    return (
        "당신은 Oracle SQL 생성기입니다. 아래 스키마만 사용해서 사용자 질문에 맞는 "
        "SELECT 문 하나만 작성하세요.\n\n"
        f"[스키마]\n{schema_desc}\n\n"
        f"[질문]\n{question}\n\n"
        "[규칙]\n"
        "- SELECT 문 하나만 출력한다.\n"
        "- 위 스키마에 없는 테이블/컬럼은 사용하지 않는다.\n"
        "- 설명, 마크다운 코드펜스, 세미콜론 없이 SQL 텍스트만 출력한다.\n"
        "- 결과 개수를 제한할 필요가 있으면 FETCH FIRST N ROWS ONLY를 사용한다."
    )


def _extract_sql(raw_response: str) -> str:
    fenced = _CODE_FENCE_RE.search(raw_response)
    text = fenced.group(1) if fenced else raw_response
    return text.strip().rstrip(";").strip()


def generate_sql(question: str) -> str:
    prompt = _build_prompt(question)
    raw_response = get_llm_client().generate(prompt)
    return _extract_sql(raw_response)
