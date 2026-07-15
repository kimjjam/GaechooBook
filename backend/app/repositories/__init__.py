"""Oracle 접근은 이 레이어를 통해서만 한다.

routers/core/nl2sql 어디에서도 SQLAlchemy 쿼리나 raw SQL을 직접 작성하지 않고,
여기 정의된 함수를 호출한다.
"""
