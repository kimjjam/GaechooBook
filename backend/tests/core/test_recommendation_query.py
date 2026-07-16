from app.core.recommendation_query import RecommendationQuery, parse_recommendation_query


def test_parses_compound_movie_constraints():
    parsed = parse_recommendation_query(
        "평가 7점 이상인 2020년 이후 한국 로맨스 영화 중 2시간 이내로 5편 추천해줘"
    )

    assert parsed.query.genres == ["로맨스"]
    assert parsed.query.min_rating == 7.0
    assert parsed.query.year_from == 2020
    assert parsed.query.country == "KR"
    assert parsed.query.max_runtime == 120
    assert parsed.query.limit == 5


def test_followup_merges_with_previous_context():
    previous = RecommendationQuery(genres=["로맨스"], min_rating=7.0).to_dict()
    parsed = parse_recommendation_query("공포는 빼고 90분 이내로 보여줘", previous)

    assert parsed.query.genres == ["로맨스"]
    assert parsed.query.min_rating == 7.0
    assert parsed.query.excluded_genres == ["공포"]
    assert parsed.query.max_runtime == 90


def test_explicit_dislike_is_marked_as_durable_feedback():
    parsed = parse_recommendation_query("공포는 싫어. 코미디로 추천해줘")

    assert parsed.query.genres == ["코미디"]
    assert parsed.query.excluded_genres == ["공포"]
    assert parsed.durable_dislikes == ["공포"]


def test_parses_similar_movie_title():
    assert parse_recommendation_query("타이타닉 같은 영화 추천해줘").query.similar_to == "타이타닉"
    assert parse_recommendation_query("타이타닉과 비슷한 작품 찾아줘").query.similar_to == "타이타닉"


def test_final_filter_rejects_movies_below_rating_or_year():
    query = RecommendationQuery(min_rating=7.0, year_from=2020, excluded_genres=["공포"])
    movies = [
        {"id": 1, "rating": 7.1, "release_year": 2020, "genres": ["로맨스"]},
        {"id": 2, "rating": 6.9, "release_year": 2024, "genres": ["로맨스"]},
        {"id": 3, "rating": 8.0, "release_year": 2019, "genres": ["로맨스"]},
        {"id": 4, "rating": 8.0, "release_year": 2024, "genres": ["공포"]},
    ]

    assert [movie["id"] for movie in query.apply(movies)] == [1]


def test_untrusted_context_values_are_safely_normalized():
    query = RecommendationQuery.from_dict({
        "genres": ["로맨스", "없는장르"],
        "min_rating": "not-a-number",
        "max_runtime": -30,
        "limit": 999,
        "sort_by": "DROP TABLE",
    })

    assert query.genres == ["로맨스"]
    assert query.min_rating is None
    assert query.max_runtime is None
    assert query.limit == 20
    assert query.sort_by == "personalized"
