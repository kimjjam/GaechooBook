"""기존 데이터를 보존하면서 사용자 개인화 컬럼을 추가한다.

실행: python -m app.scripts.migrate_personalization
"""
from sqlalchemy import inspect, text

from app.db.models import AuthSession, Base, User
from app.db.oracle_client import _get_engine


_COLUMNS = {
    "USERS": {
        "EMAIL": "VARCHAR2(320)",
        "PASSWORD_HASH": "VARCHAR2(512)",
        "NICKNAME": "VARCHAR2(50)",
        "FAILED_LOGIN_ATTEMPTS": "NUMBER DEFAULT 0 NOT NULL",
        "LOCKED_UNTIL": "TIMESTAMP",
        "LAST_LOGIN_AT": "TIMESTAMP",
    },
    "USER_TASTE_PROFILE": {
        "USER_ID": "NUMBER",
    },
    "ONBOARDING_SIGNALS": {
        "USER_ID": "NUMBER",
    },
    "INTERACTIONS": {
        "USER_ID": "NUMBER",
        "TMDB_MOVIE_ID": "NUMBER",
        "MOVIE_TITLE": "VARCHAR2(200)",
        "MOVIE_GENRES": "VARCHAR2(500)",
    },
}


def migrate() -> None:
    engine = _get_engine()
    User.__table__.create(engine, checkfirst=True)

    inspector = inspect(engine)
    existing_tables = {name.upper() for name in inspector.get_table_names()}
    with engine.begin() as connection:
        for table_name, columns in _COLUMNS.items():
            if table_name not in existing_tables:
                continue
            existing_columns = {
                column[0]
                for column in connection.execute(
                    text(
                        "SELECT column_name FROM user_tab_columns "
                        "WHERE table_name = :table_name"
                    ),
                    {"table_name": table_name},
                )
            }
            for column_name, column_type in columns.items():
                if column_name not in existing_columns:
                    connection.execute(
                        text(f"ALTER TABLE {table_name} ADD ({column_name} {column_type})")
                    )

        visitor_nullable = connection.execute(
            text(
                "SELECT nullable FROM user_tab_columns "
                "WHERE table_name = 'USERS' AND column_name = 'VISITOR_TOKEN'"
            )
        ).scalar()
        if visitor_nullable == "N":
            connection.execute(text("ALTER TABLE USERS MODIFY (VISITOR_TOKEN NULL)"))

        email_index_exists = connection.execute(
            text("SELECT COUNT(*) FROM user_indexes WHERE index_name = 'UQ_USERS_EMAIL_CI'")
        ).scalar()
        if not email_index_exists:
            connection.execute(text("CREATE UNIQUE INDEX UQ_USERS_EMAIL_CI ON USERS (LOWER(EMAIL))"))

    # 새로 설치하는 환경에서도 전체 테이블을 한 번에 생성할 수 있게 한다.
    AuthSession.__table__.create(engine, checkfirst=True)
    Base.metadata.create_all(engine)


if __name__ == "__main__":
    migrate()
    print("personalization migration complete")
