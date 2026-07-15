"""도서 검색 API 응답을 공통 형식으로 정리하는 도우미."""

from __future__ import annotations

import html
import re


_HTML_TAG_RE = re.compile(r"<[^>]+>")
_YEAR_RE = re.compile(r"(19|20)\d{2}")


def clean_text(value: object) -> str | None:
    if value is None:
        return None
    text = html.unescape(_HTML_TAG_RE.sub("", str(value))).strip()
    return text or None


def publication_year(value: object) -> int | None:
    if value is None:
        return None
    match = _YEAR_RE.search(str(value))
    return int(match.group(0)) if match else None


def normalize_isbn(value: object) -> str | None:
    if value is None:
        return None
    candidates = re.findall(r"[0-9Xx]{10,13}", re.sub(r"[-\s]", "", str(value)))
    if not candidates:
        return None
    return next((isbn for isbn in candidates if len(isbn) == 13), candidates[0]).upper()
