import type { AuthSession } from "@/features/chat/types";
import { apiFetch } from "@/lib/api/personalizationClient";

export async function getAuthSession(): Promise<AuthSession | null> {
  return apiFetch<AuthSession | null>("/auth/session");
}

export function register(input: {
  visitorToken: string;
  email: string;
  password: string;
  nickname: string;
}): Promise<AuthSession> {
  return apiFetch("/auth/register", {
    method: "POST",
    body: JSON.stringify({
      visitor_token: input.visitorToken,
      email: input.email,
      password: input.password,
      nickname: input.nickname,
    }),
  });
}

export function login(email: string, password: string): Promise<AuthSession> {
  return apiFetch("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function logout(csrfToken: string): Promise<{ logged_out: boolean }> {
  return apiFetch("/auth/logout", {
    method: "POST",
    headers: { "X-CSRF-Token": csrfToken },
  });
}
