"use client";

import { useState } from "react";
import { sendChatMessage } from "@/lib/api/chatClient";
import type { ChatMessage } from "@/features/chat/types";

interface ChatWindowProps {
  sessionId: string;
}

export function ChatWindow({ sessionId }: ChatWindowProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || isLoading) return;

    setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "user", text }]);
    setInput("");
    setIsLoading(true);
    setError(null);

    try {
      const response = await sendChatMessage(sessionId, text);
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

  return (
    <div className="flex flex-1 flex-col gap-3">
      <div className="flex-1 space-y-2 overflow-y-auto rounded border p-3">
        {messages.map((m) => (
          <div
            key={m.id}
            className={m.role === "user" ? "text-right" : "text-left"}
          >
            <span
              className={
                m.role === "user"
                  ? "inline-block rounded bg-blue-500 px-3 py-1.5 text-white"
                  : "inline-block rounded bg-gray-100 px-3 py-1.5"
              }
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
          placeholder="메시지를 입력하세요"
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
