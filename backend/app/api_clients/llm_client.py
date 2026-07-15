"""NL2SQL 생성에 사용하는 Gemini 클라이언트."""
import os

from dotenv import load_dotenv

load_dotenv()


class GeminiClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")

    def generate(self, prompt: str) -> str:
        import google.generativeai as genai

        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY가 설정되지 않았습니다.")
        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-3.5-flash"))
        response = model.generate_content(prompt)
        return response.text


def get_gemini_client() -> GeminiClient:
    return GeminiClient()
