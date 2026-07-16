import type {
  MovieDetail,
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

interface ValidationErrorDetail {
  loc?: Array<string | number>;
  msg?: string;
}

function getErrorMessage(body: unknown, status: number): string {
  if (typeof body !== "object" || body === null || !("detail" in body)) {
    return `서버 응답 오류: ${status}`;
  }

  const { detail } = body as { detail?: unknown };
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item: ValidationErrorDetail) => {
        if (!item || typeof item.msg !== "string") return null;
        const field = item.loc?.filter((part) => part !== "body").join(".");
        return field ? `${field}: ${item.msg}` : item.msg;
      })
      .filter((message): message is string => Boolean(message));
    if (messages.length > 0) return messages.join(", ");
  }
  return `서버 응답 오류: ${status}`;
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    throw new ApiError(getErrorMessage(body, response.status), response.status);
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
  excludeMovieIds: number[] = [],
): Promise<MovieRecommendation[]> {
  const params = new URLSearchParams({ limit: "10" });
  if (excludeMovieIds.length > 0) {
    params.set("exclude_movie_ids", excludeMovieIds.join(","));
  }
  const result = await apiFetch<{ recommendations: MovieRecommendation[] }>(
    `/personalization/recommendations?${params.toString()}`,
    { headers: { "X-Visitor-Token": visitorToken } },
  );
  return result.recommendations;
}

export function getMovieDetail(movieId: number): Promise<MovieDetail> {
  return apiFetch(`/personalization/movies/${movieId}`);
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
