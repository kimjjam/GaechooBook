from app.core.scoring.books import rank_books


def _book(title: str, description: str, source: str, index: int) -> dict:
    return {
        "title": title,
        "description": description,
        "genre": "과학",
        "isbn": f"9781234567{index:03d}",
        "sources": [source],
    }


def test_adult_recommendations_exclude_school_workbooks():
    preferences = {
        "genre": "과학·기술",
        "topic": "새로운 지식",
        "reading_mood": "가볍고 편하게",
        "age_group": "30대",
        "mbti": "ISTP",
    }
    books = [
        _book("초등 과학 문제집", "교과서 자습서", "네이버", 1),
        _book("일상 속 과학 원리", "쉽고 재미있는 기술 탐구", "알라딘", 2),
    ]

    ranked = rank_books(books, preferences, limit=5)

    assert [book["title"] for book in ranked] == ["일상 속 과학 원리"]


def test_school_workbooks_are_excluded_for_every_age_group():
    preferences = {
        "genre": "과학·기술",
        "topic": "새로운 지식",
        "reading_mood": "가볍고 편하게",
        "age_group": "초등학생",
        "mbti": "ENFP",
    }
    books = [
        _book("초등 과학 평가문제집", "시험대비 기출문제", "네이버", 1),
        _book("어린이를 위한 우주 이야기", "재미있는 과학 교양", "카카오", 2),
    ]

    ranked = rank_books(books, preferences, limit=5)

    assert [book["title"] for book in ranked] == ["어린이를 위한 우주 이야기"]


def test_mbti_is_a_secondary_ranking_signal():
    base_preferences = {
        "genre": "과학·기술",
        "topic": "새로운 지식",
        "reading_mood": "깊이 생각하며",
        "age_group": "20대",
        "mbti": "ISTP",
    }
    books = [
        _book("과학의 역사", "새로운 지식을 소개한다", "네이버", 1),
        _book("기술 탐구 생활", "새로운 지식과 실용적인 원리", "알라딘", 2),
    ]

    ranked = rank_books(books, base_preferences, limit=2)

    assert ranked[0]["title"] == "기술 탐구 생활"
    assert "ISTP" in ranked[0]["recommendation_reason"]


def test_selection_limits_one_provider_dominance():
    preferences = {
        "genre": "소설",
        "topic": "몰입과 재미",
        "reading_mood": "빠르게 몰입해서",
        "age_group": "40대",
        "mbti": "ENFP",
    }
    books = [
        _book(f"모험 소설 {index}", "재미있는 이야기", "네이버", index)
        for index in range(4)
    ] + [
        _book("알라딘 소설", "몰입하는 이야기", "알라딘", 10),
        _book("카카오 소설", "몰입하는 이야기", "카카오", 11),
    ]

    ranked = rank_books(books, preferences, limit=5)

    assert [book["sources"][0] for book in ranked[:4]] == [
        "네이버", "네이버", "알라딘", "카카오",
    ]
