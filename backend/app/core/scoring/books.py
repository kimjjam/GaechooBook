"""도서 후보를 연령 적합성, 현재 취향, MBTI 보조 신호로 정렬한다."""

from __future__ import annotations

import re
from collections import Counter


_STUDY_MATERIAL_KEYWORDS = (
    "수능", "내신", "교과서", "자습서", "문제집",
    "학습지", "참고서", "기출", "모의고사", "수험서", "워크북", "ebs",
    "수능특강", "평가문제", "완자", "n제", "시험대비", "족보",
)
_AGE_EXCLUSIONS = {
    "초등학생": ("중등", "고등", "수능", "대학", "성인"),
    "중학생": ("초등", "고등", "수능"),
    "고등학생": ("초등", "중등"),
}
_ADULT_AGE_GROUPS = {"20대", "30대", "40대", "50대 이상"}

_MBTI_KEYWORDS = {
    "ISTJ": ("체계", "원칙", "역사", "기록", "실용"),
    "ISFJ": ("공감", "가족", "관계", "위로", "따뜻"),
    "INFJ": ("내면", "의미", "심리", "철학", "성찰"),
    "INTJ": ("전략", "통찰", "미래", "과학", "분석"),
    "ISTP": ("탐구", "기술", "과학", "실용", "원리"),
    "ISFP": ("감성", "예술", "위로", "자연", "문장"),
    "INFP": ("상상", "감정", "성장", "판타지", "문학"),
    "INTP": ("관점", "이론", "과학", "철학", "지식"),
    "ESTP": ("모험", "액션", "도전", "현장", "속도"),
    "ESFP": ("유쾌", "재미", "여행", "사람", "생생"),
    "ENFP": ("영감", "가능성", "창의", "성장", "모험"),
    "ENTP": ("발상", "논쟁", "혁신", "아이디어", "관점"),
    "ESTJ": ("목표", "성과", "경영", "습관", "실용"),
    "ESFJ": ("관계", "소통", "가족", "공감", "따뜻"),
    "ENFJ": ("성장", "공감", "리더십", "관계", "변화"),
    "ENTJ": ("리더십", "전략", "경영", "성취", "미래"),
}
_MOOD_KEYWORDS = {
    "가볍고 편하게": ("쉽게", "가볍", "재미", "이야기", "교양"),
    "깊이 생각하며": ("철학", "인문", "성찰", "통찰", "사유"),
    "빠르게 몰입해서": ("미스터리", "추리", "스릴러", "모험", "소설"),
    "따뜻하게 쉬면서": ("위로", "따뜻", "마음", "에세이", "힐링"),
}


def _book_text(book: dict) -> str:
    return " ".join(
        str(book.get(field) or "")
        for field in ("title", "description", "genre", "publisher")
    ).casefold()


def _preference_tokens(value: str) -> list[str]:
    return [token.casefold() for token in re.findall(r"[0-9A-Za-z가-힣]+", value) if len(token) >= 2]


def _age_appropriate(text: str, age_group: str) -> bool:
    if any(keyword in text for keyword in _STUDY_MATERIAL_KEYWORDS):
        return False
    if age_group in _ADULT_AGE_GROUPS:
        return not any(keyword in text for keyword in ("초등", "중등", "고등"))
    return not any(keyword in text for keyword in _AGE_EXCLUSIONS.get(age_group, ()))


def _score_book(book: dict, preferences: dict[str, str]) -> tuple[float, list[str]]:
    text = _book_text(book)
    score = 0.0
    reasons: list[str] = []

    genre_matches = sum(token in text for token in _preference_tokens(preferences.get("genre", "")))
    if genre_matches:
        score += genre_matches * 3.0
        reasons.append(preferences["genre"])

    topic_matches = sum(token in text for token in _preference_tokens(preferences.get("topic", "")))
    if topic_matches:
        score += topic_matches * 2.2
        reasons.append(preferences["topic"])

    mood = preferences.get("reading_mood", "")
    if any(keyword in text for keyword in _MOOD_KEYWORDS.get(mood, ())):
        score += 1.2
        reasons.append(mood)

    mbti = preferences.get("mbti", "").upper()
    if any(keyword in text for keyword in _MBTI_KEYWORDS.get(mbti, ())):
        score += 0.8
        reasons.append(f"{mbti} 탐색 성향")

    return score, reasons


def rank_books(
    books: list[dict],
    preferences: dict[str, str],
    limit: int = 5,
) -> list[dict]:
    """부적합 학습서를 제거하고, 점수와 제공자 다양성을 함께 반영한다."""
    age_group = preferences.get("age_group", "")
    scored: list[tuple[float, int, dict]] = []
    for index, book in enumerate(books):
        if age_group and not _age_appropriate(_book_text(book), age_group):
            continue
        score, reasons = _score_book(book, preferences)
        reason_parts = list(dict.fromkeys(reasons[:2]))
        mbti_reason = next((reason for reason in reasons if "탐색 성향" in reason), None)
        if mbti_reason and mbti_reason not in reason_parts:
            if len(reason_parts) >= 2:
                reason_parts[-1] = mbti_reason
            else:
                reason_parts.append(mbti_reason)
        reason = " · ".join(reason_parts) or f"{age_group or '현재 취향'}에 맞는 도서"
        scored.append((score, index, {**book, "recommendation_reason": reason}))

    scored.sort(key=lambda item: (-item[0], item[1]))
    ranked = [book for _score, _index, book in scored]

    selected: list[dict] = []
    selected_ids: set[int] = set()
    source_counts: Counter[str] = Counter()
    for index, book in enumerate(ranked):
        source = (book.get("sources") or ["기타"])[0]
        if source_counts[source] >= 2:
            continue
        selected.append(book)
        selected_ids.add(index)
        source_counts[source] += 1
        if len(selected) >= limit:
            return selected

    for index, book in enumerate(ranked):
        if index in selected_ids:
            continue
        selected.append(book)
        if len(selected) >= limit:
            break
    return selected
