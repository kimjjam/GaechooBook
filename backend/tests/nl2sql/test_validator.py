import pytest

from app.nl2sql.validator import SQLValidationError, validate_sql

ALLOWED = {"movies", "books"}


def test_select_passes():
    sql = "SELECT title, rating FROM movies WHERE release_year > 2010"
    assert validate_sql(sql, ALLOWED) == sql


def test_delete_is_blocked():
    with pytest.raises(SQLValidationError):
        validate_sql("DELETE FROM movies WHERE id = 1", ALLOWED)


def test_update_is_blocked():
    with pytest.raises(SQLValidationError):
        validate_sql("UPDATE movies SET rating = 10", ALLOWED)


def test_drop_is_blocked():
    with pytest.raises(SQLValidationError):
        validate_sql("SELECT * FROM movies; DROP TABLE movies", ALLOWED)


def test_table_outside_whitelist_is_blocked():
    with pytest.raises(SQLValidationError):
        validate_sql("SELECT * FROM user_taste_profile", ALLOWED)


def test_multiple_statements_blocked():
    with pytest.raises(SQLValidationError):
        validate_sql("SELECT * FROM movies; SELECT * FROM books", ALLOWED)
