"""Oracle 연결(raw pool + SQLAlchemy engine)과 ORM 모델을 모아두는 레이어.

이 레이어 밖(routers, nl2sql 등)에서는 oracledb/SQLAlchemy를 직접 import하지 않는다.
"""
