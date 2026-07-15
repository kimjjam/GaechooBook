export type Intent = "recommend" | "nl2sql" | "visualize" | "chitchat";

export interface ChatResponse {
  intent: Intent;
  reply: string;
  data?: Record<string, unknown> | null;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
}

export interface TasteProfile {
  visitor_token: string;
  onboarding_completed: boolean;
  favorite_genres: string[];
  moods: string[];
}

export interface MovieRecommendation {
  id: number;
  title: string;
  overview: string;
  poster_url?: string | null;
  release_year?: number | null;
  rating: number;
  genres: string[];
  score: number;
  reason: string;
}

export interface AuthSession {
  user: {
    id: number;
    email: string;
    nickname: string;
  };
  csrf_token: string;
}
