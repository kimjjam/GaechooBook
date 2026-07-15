import type {
  MovieRecommendation,
  TasteProfile,
} from "@/features/chat/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api/backend";

interface OnboardingInput {
  visitor_token: string;
  favorite_genres: string[];
  moods: string[];
  favorite_movie?: string;
}

export class ApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new ApiError(body?.detail ?? `서버 응답 오류: ${response.status}`, response.status);
  }
  return response.json() as Promise<T>;
}

export function getProfile(visitorToken: string): Promise<TasteProfile> {
  return apiFetch("/personalization/profile", {
    headers: { "X-Visitor-Token": visitorToken },
  });
}

export function saveOnboarding(input: OnboardingInput, csrfToken?: string): Promise<TasteProfile> {
  return apiFetch("/personalization/onboarding", {
    method: "POST",
    headers: csrfToken ? { "X-CSRF-Token": csrfToken } : undefined,
    body: JSON.stringify(input),
  });
}

export async function getRecommendations(
  visitorToken: string,
): Promise<MovieRecommendation[]> {
  const result = await apiFetch<{ recommendations: MovieRecommendation[] }>(
    "/personalization/recommendations?limit=10",
    { headers: { "X-Visitor-Token": visitorToken } },
  );
  return result.recommendations;
}

export function sendFeedback(
  visitorToken: string,
  movie: MovieRecommendation,
  action: "liked" | "disliked",
  csrfToken?: string,
): Promise<{ saved: boolean; message: string }> {
  return apiFetch("/personalization/feedback", {
    method: "POST",
    headers: csrfToken ? { "X-CSRF-Token": csrfToken } : undefined,
    body: JSON.stringify({
      visitor_token: visitorToken,
      movie_id: movie.id,
      movie_title: movie.title,
      genres: movie.genres,
      action,
    }),
  });
}
