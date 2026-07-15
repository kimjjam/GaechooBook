from app.routers.classify import classify_utterance
from app.schemas.chat import Intent


def test_recommend_example_from_proposal():
    # 제안서 2.1 예시
    assert (
        classify_utterance("요즘 야근이 많아서 가볍게 웃을 수 있는 거 보고 싶어")
        == Intent.RECOMMEND
    )


def test_nl2sql_example_from_proposal():
    # 제안서 2.2 예시 — "보여줘"가 있어도 NL2SQL로 분류되어야 한다
    assert (
        classify_utterance("2010년대 개봉한 한국 영화 중 평점 높은 순으로 5개 보여줘")
        == Intent.NL2SQL
    )


def test_visualize_example_from_proposal():
    # 제안서 2.3 예시
    assert classify_utterance("내 장르 취향 분포 보여줘") == Intent.VISUALIZE


def test_chitchat_fallback():
    assert classify_utterance("안녕") == Intent.CHITCHAT


def test_book_search_is_routed_to_recommendation():
    assert classify_utterance("해리포터 책 검색해줘") == Intent.RECOMMEND
