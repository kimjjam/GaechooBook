"""발화 분류만 담당한다. 분류 결과를 어떻게 처리할지는 chat.py의 몫이다.

지금은 키워드 기반 더미 로직이다. 실제 LLM 분류(few-shot 프롬프트)는
3단계에서 llm_client.py와 함께 구현한다.
"""
from app.schemas.chat import Intent

# "보여줘"처럼 여러 intent에 공통으로 나오는 표현은 제외하고, 그 intent에서만
# 쓰이는 표현으로 좁힌다 (예: 제안서 2.2의 "...평점 높은 순으로 5개 보여줘"는
# NL2SQL이지 시각화가 아니다).
_VISUALIZE_KEYWORDS = ("분포", "차트", "그래프", "지도")
_NL2SQL_KEYWORDS = ("몇 개", "평점", "년도", "연도", "국가", "순위", "순으로")
_RECOMMEND_KEYWORDS = ("추천", "보고싶", "보고 싶", "읽고싶", "읽고 싶")
_BOOK_KEYWORDS = ("책", "도서", "소설", "에세이", "자기계발", "인문학")
_BOOK_SEARCH_ACTIONS = ("검색", "찾아", "추천", "읽고")


def classify_utterance(message: str) -> Intent:
    text = message.strip()

    if any(keyword in text for keyword in _VISUALIZE_KEYWORDS):
        return Intent.VISUALIZE
    if (
        any(keyword in text for keyword in _BOOK_KEYWORDS)
        and any(keyword in text for keyword in _BOOK_SEARCH_ACTIONS)
    ):
        return Intent.RECOMMEND
    if any(keyword in text for keyword in _RECOMMEND_KEYWORDS):
        return Intent.RECOMMEND
    if any(keyword in text for keyword in _NL2SQL_KEYWORDS):
        return Intent.NL2SQL
    return Intent.CHITCHAT
