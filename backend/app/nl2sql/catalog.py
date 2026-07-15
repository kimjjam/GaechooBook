"""NL2SQL 프롬프트 및 validator 화이트리스트의 단일 소스.

스키마가 바뀌면 이 파일만 수정한다 (다른 곳에 테이블/컬럼 설명을 중복
하드코딩하지 않는다).
"""

CATALOG: dict[str, dict] = {
    "movies": {
        "description": "영화 메타데이터",
        "columns": {
            "id": "고유 ID",
            "title": "영화 제목",
            "release_year": "개봉연도",
            "genre": "장르 (콤마구분)",
            "rating": "평균 평점 (0~10)",
            "country": "제작 국가",
        },
    },
    "books": {
        "description": "도서 메타데이터",
        "columns": {
            "id": "고유 ID",
            "title": "책 제목",
            "author": "저자",
            "genre": "장르",
            "pub_year": "출판연도",
        },
    },
}


def allowed_tables() -> set[str]:
    return set(CATALOG.keys())


def allowed_columns(table: str) -> set[str]:
    return set(CATALOG.get(table, {}).get("columns", {}).keys())
