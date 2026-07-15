"use client";

import { useState } from "react";
import { sendChatMessage } from "@/lib/api/chatClient";
import type { ChatMessage } from "@/features/chat/types";

interface ChatWindowProps {
  sessionId: string;
  mode?: "general" | "movies" | "books";
}

const BOOK_SUGGESTIONS = [
  "요즘 읽기 좋은 소설 추천해줘",
  "마음이 편안해지는 에세이 추천해줘",
  "몰입감 좋은 과학 도서 추천해줘",
];

const MOVIE_SUGGESTIONS = [
  "오늘은 공포영화 추천해줘",
  "가볍게 웃을 수 있는 영화 추천해줘",
  "몰입감 좋은 SF 영화 추천해줘",
];

export function ChatWindow({ sessionId, mode = "general" }: ChatWindowProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function sendMessage(text: string) {
    if (!text || isLoading) return;

    setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "user", text }]);
    setInput("");
    setIsLoading(true);
    setError(null);

    try {
      const requestText = mode === "books" && !/(책|도서|소설|에세이|자기계발|인문학)/.test(text)
        ? `도서 추천: ${text}`
        : text;
      const response = await sendChatMessage(sessionId, requestText);
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: "assistant", text: response.reply },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "알 수 없는 오류가 발생했습니다.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    await sendMessage(input.trim());
  }

  return (
    <div className="chat-window">
      <div className="chat-history" aria-live="polite">
        {messages.length === 0 && mode === "books" && (
          <div className="chat-empty-state">
            <strong>어떤 책을 찾고 있나요?</strong>
            <span>장르, 관심사 또는 지금 기분을 편하게 적어주세요.</span>
            <div className="prompt-suggestions">
              {BOOK_SUGGESTIONS.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => void sendMessage(suggestion)}
                  disabled={isLoading}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.length === 0 && mode === "movies" && (
          <div className="chat-empty-state">
            <strong>오늘은 어떤 영화가 끌리나요?</strong>
            <span>평소 취향과 달라도 괜찮아요. 오늘의 요청도 가볍게 기억할게요.</span>
            <div className="prompt-suggestions">
              {MOVIE_SUGGESTIONS.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => void sendMessage(suggestion)}
                  disabled={isLoading}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m) => (
          <div
            key={m.id}
            className={`chat-row ${m.role}`}
          >
            {m.role === "assistant" && <span className="chat-avatar" aria-hidden="true">M</span>}
            <span className="chat-bubble">
              {m.text}
            </span>
          </div>
        ))}
        {isLoading && (
          <div className="chat-row assistant" aria-label="답변을 작성하고 있어요">
            <span className="chat-avatar" aria-hidden="true">M</span>
            <span className="chat-bubble typing-indicator" aria-hidden="true">
              <i /><i /><i />
            </span>
          </div>
        )}
        {error && <p className="chat-error" role="alert">{error}</p>}
      </div>
      <form onSubmit={handleSubmit} className="chat-composer">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={
            mode === "books"
              ? "예: 비 오는 날 읽을 추리소설 추천해줘"
              : mode === "movies"
                ? "예: 오늘은 공포영화 추천해줘"
                : "메시지를 입력하세요"
          }
        />
        <button
          type="submit"
          className="chat-send-button"
          disabled={isLoading || !input.trim()}
          aria-label="메시지 보내기"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M12 19V5m0 0-6 6m6-6 6 6" />
          </svg>
        </button>
      </form>
    </div>
  );
}
