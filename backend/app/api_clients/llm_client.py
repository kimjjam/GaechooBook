"""발화 분류, 대화 신호 추출, NL2SQL 생성에 쓰이는 LLM 클라이언트.

LLM_PROVIDER 환경변수(gemini|claude)로 어떤 구현체를 쓸지 고른다.
"""
import os
from abc import ABC, abstractmethod

from dotenv import load_dotenv

load_dotenv()


class LLMClient(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        ...


class GeminiClient(LLMClient):
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")

    def generate(self, prompt: str) -> str:
        import google.generativeai as genai

        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-3.5-flash"))
        response = model.generate_content(prompt)
        return response.text


class ClaudeClient(LLMClient):
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")

    def generate(self, prompt: str) -> str:
        import anthropic

        client = anthropic.Anthropic(api_key=self.api_key)
        response = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=1024,
            thinking={"type": "adaptive"},
            messages=[{"role": "user", "content": prompt}],
        )
        return next((block.text for block in response.content if block.type == "text"), "")


def get_llm_client() -> LLMClient:
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    if provider == "claude":
        return ClaudeClient()
    return GeminiClient()
