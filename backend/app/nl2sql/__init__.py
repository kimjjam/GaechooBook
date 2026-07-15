"""자연어 질의 → SQL 파이프라인.

catalog.py(스키마 설명) → generator.py(LLM SQL 생성) → validator.py(안전 검증)
→ executor.py(검증된 SQL만 실행) 순서로 흐른다. validator를 우회하는 경로를
만들지 않는다.
"""
