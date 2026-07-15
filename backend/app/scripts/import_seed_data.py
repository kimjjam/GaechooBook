"""테스트/데모용 시드 데이터를 Oracle movies/books 테이블에 채운다.

1회성 수동 실행 스크립트: backend/ 에서 `python -m app.scripts.import_seed_data`
이미 존재하는 title은 건너뛰어 중복 삽입을 피한다(재실행해도 안전).
"""
from app.api_clients.kakao_books import KakaoBooksClient
from app.api_clients.tmdb import TMDBClient
from app.db.models import Book, Movie
from app.db.oracle_client import get_session


def import_movies() -> int:
    movies = TMDBClient().collect_seed_movies()
    inserted = 0
    with get_session() as session:
        existing_titles = {row[0] for row in session.query(Movie.title).all()}
        for movie in movies:
            if movie["title"] in existing_titles:
                continue
            session.add(Movie(**movie))
            existing_titles.add(movie["title"])
            inserted += 1
        session.commit()
    return inserted


def import_books() -> int:
    books = KakaoBooksClient().collect_seed_books()
    inserted = 0
    with get_session() as session:
        existing_titles = {row[0] for row in session.query(Book.title).all()}
        for book in books:
            if book["title"] in existing_titles:
                continue
            session.add(Book(**book))
            existing_titles.add(book["title"])
            inserted += 1
        session.commit()
    return inserted


if __name__ == "__main__":
    movie_count = import_movies()
    book_count = import_books()
    print(f"movies inserted: {movie_count}")
    print(f"books inserted: {book_count}")
