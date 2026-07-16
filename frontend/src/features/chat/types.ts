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
  movies?: MovieRecommendation[];
  books?: BookRecommendation[];
}

export interface BookRecommendation {
  title: string;
  author?: string | null;
  publisher?: string | null;
  pub_year?: number | null;
  isbn?: string | null;
  thumbnail_url?: string | null;
  description?: string | null;
  link?: string | null;
  genre?: string | null;
  sources: string[];
  recommendation_reason?: string | null;
}

export interface RecommendationContext {
  genres?: string[];
  excluded_genres?: string[];
  moods?: string[];
  min_rating?: number | null;
  max_rating?: number | null;
  year_from?: number | null;
  year_to?: number | null;
  max_runtime?: number | null;
  country?: string | null;
  country_name?: string | null;
  similar_to?: string | null;
  limit?: number;
  sort_by?: string;
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

export interface MovieDetail {
  id: number;
  title: string;
  overview: string;
  poster_url?: string | null;
  backdrop_url?: string | null;
  release_year?: number | null;
  release_date?: string | null;
  runtime?: number | null;
  rating: number;
  genres: string[];
  tagline?: string | null;
  trailer_url?: string | null;
}

export interface AuthSession {
  user: {
    id: number;
    email: string;
    nickname: string;
  };
  csrf_token: string;
}
