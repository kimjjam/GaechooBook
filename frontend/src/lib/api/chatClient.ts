import type { ChatResponse } from "@/features/chat/types";

export interface BookPreferences {
  genre: string;
  topic: string;
  reading_mood: string;
  age_group: string;
  mbti: string;
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api/backend";

export async function sendChatMessage(
  sessionId: string,
  message: string,
  recommendationContext?: Record<string, unknown> | null,
  excludeMovieIds: number[] = [],
  bookPreferences?: BookPreferences | null,
): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      message,
      recommendation_context: recommendationContext,
      exclude_movie_ids: excludeMovieIds,
      book_preferences: bookPreferences,
    }),
  });

  if (!res.ok) {
    throw new Error(`백엔드 응답 오류: ${res.status}`);
  }

  return res.json() as Promise<ChatResponse>;
}
