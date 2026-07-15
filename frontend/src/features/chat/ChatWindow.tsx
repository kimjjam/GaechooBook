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
    <div className="flex flex-1 flex-col gap-3">
      <div className="flex-1 space-y-2 overflow-y-auto rounded border p-3">
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
            className={m.role === "user" ? "text-right" : "text-left"}
          >
            <span
              className={`chat-message ${
                m.role === "user"
                  ? "inline-block rounded bg-blue-500 px-3 py-1.5 text-white"
                  : "inline-block rounded bg-gray-100 px-3 py-1.5"
              }`}
            >
              {m.text}
            </span>
          </div>
        ))}
        {isLoading && <p className="text-sm text-gray-400">응답 대기 중...</p>}
        {error && <p className="text-sm text-red-500">{error}</p>}
      </div>
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          className="flex-1 rounded border px-3 py-2"
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
          className="rounded bg-blue-500 px-4 py-2 text-white disabled:opacity-50"
          disabled={isLoading}
        >
          전송
        </button>
      </form>
    </div>
  );
}
