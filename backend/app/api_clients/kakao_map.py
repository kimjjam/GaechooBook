import os


class KakaoMapClient:
    """근처 서점/도서관 검색 등 지도 기능용. 실제 HTTP 호출은 5단계(시각화/지도)에서 구현."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("KAKAO_MAP_API_KEY", "")

    def search_nearby(self, keyword: str, lat: float, lng: float) -> list[dict]:
        raise NotImplementedError("Kakao Map 연동은 5단계(시각화/지도)에서 구현 예정")
