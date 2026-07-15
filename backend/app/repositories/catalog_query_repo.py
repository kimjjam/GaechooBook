"""movies/books(NL2SQL 조회 대상 원본 데이터) 접근 레이어.

run_select()는 nl2sql/validator.py를 통과한 SQL만 실행한다(검증은 여기서
하지 않는다). list_top_movies/list_top_books는 과제용 카탈로그 조회에 남겨둔
헬퍼다. 메인 영화 추천은 TMDB API와 사용자 취향 프로필을 사용한다.
"""
from app.db.models import Book, Movie
from app.db.oracle_client import get_connection, get_session


def run_select(sql: str) -> list[dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql)
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def list_top_movies(genre_keyword: str | None = None, limit: int = 5) -> list[Movie]:
    with get_session() as session:
        query = session.query(Movie)
        if genre_keyword:
            query = query.filter(Movie.genre.ilike(f"%{genre_keyword}%"))
        return query.order_by(Movie.rating.desc()).limit(limit).all()


def list_top_books(genre_keyword: str | None = None, limit: int = 5) -> list[Book]:
    with get_session() as session:
        query = session.query(Book)
        if genre_keyword:
            query = query.filter(Book.genre.ilike(f"%{genre_keyword}%"))
        return query.order_by(Book.pub_year.desc()).limit(limit).all()
