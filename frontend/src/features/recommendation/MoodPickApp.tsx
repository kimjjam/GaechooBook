"use client";

import { useEffect, useState } from "react";

import { AuthPanel } from "@/features/auth/AuthPanel";
import { ChatWindow } from "@/features/chat/ChatWindow";
import type { AuthSession, MovieRecommendation, TasteProfile } from "@/features/chat/types";
import { OnboardingForm } from "@/features/onboarding/OnboardingForm";
import { RecommendationGrid } from "@/features/recommendation/RecommendationGrid";
import {
  getProfile,
  getRecommendations,
  saveOnboarding,
  sendFeedback,
} from "@/lib/api/personalizationClient";
import { getAuthSession, logout } from "@/lib/api/authClient";

const VISITOR_TOKEN_KEY = "moodpick_visitor_token";

function getVisitorToken(): string {
  const stored = localStorage.getItem(VISITOR_TOKEN_KEY);
  if (stored) return stored;
  const token = crypto.randomUUID();
  localStorage.setItem(VISITOR_TOKEN_KEY, token);
  return token;
}

export function MoodPickApp() {
  const [visitorToken, setVisitorToken] = useState("");
  const [profile, setProfile] = useState<TasteProfile | null>(null);
  const [authSession, setAuthSession] = useState<AuthSession | null>(null);
  const [movies, setMovies] = useState<MovieRecommendation[]>([]);
  const [isBooting, setIsBooting] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isEditingTaste, setIsEditingTaste] = useState(false);
  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const token = getVisitorToken();
    setVisitorToken(token);

    async function restoreVisitor() {
      try {
        const restoredSession = await getAuthSession();
        if (cancelled) return;
        setAuthSession(restoredSession);
        const restoredProfile = await getProfile(token);
        if (cancelled) return;
        setProfile(restoredProfile);
        if (restoredProfile.onboarding_completed) {
          const recommendations = await getRecommendations(token);
          if (!cancelled) setMovies(recommendations);
        }
      } catch (caught) {
        if (!cancelled) setError(caught instanceof Error ? caught.message : "서비스를 불러오지 못했습니다.");
      } finally {
        if (!cancelled) setIsBooting(false);
      }
    }

    void restoreVisitor();
    return () => {
      cancelled = true;
    };
  }, []);

  async function refreshRecommendations() {
    if (!visitorToken) return;
    setIsRefreshing(true);
    setError(null);
    try {
      setMovies(await getRecommendations(visitorToken));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "추천을 불러오지 못했습니다.");
    } finally {
      setIsRefreshing(false);
    }
  }

  async function handleOnboarding(input: {
    favoriteGenres: string[];
    moods: string[];
    favoriteMovie: string;
  }) {
    setError(null);
    try {
      const savedProfile = await saveOnboarding({
        visitor_token: visitorToken,
        favorite_genres: input.favoriteGenres,
        moods: input.moods,
        favorite_movie: input.favoriteMovie || undefined,
      }, authSession?.csrf_token);
      setProfile(savedProfile);
      setIsEditingTaste(false);
      setMovies(await getRecommendations(visitorToken));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "취향을 저장하지 못했습니다.");
      throw caught;
    }
  }

  async function handleFeedback(movie: MovieRecommendation, action: "liked" | "disliked") {
    setError(null);
    try {
      await sendFeedback(visitorToken, movie, action, authSession?.csrf_token);
      setMovies((current) => current.filter((item) => item.id !== movie.id));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "평가를 저장하지 못했습니다.");
    }
  }

  async function handleAuthenticated(session: AuthSession) {
    setAuthSession(session);
    setIsAuthOpen(false);
    setError(null);
    const restoredProfile = await getProfile(visitorToken);
    setProfile(restoredProfile);
    setIsEditingTaste(false);
    setMovies(
      restoredProfile.onboarding_completed
        ? await getRecommendations(visitorToken)
        : [],
    );
  }

  async function handleLogout() {
    if (!authSession) return;
    setError(null);
    try {
      await logout(authSession.csrf_token);
      setAuthSession(null);
      const anonymousProfile = await getProfile(visitorToken);
      setProfile(anonymousProfile);
      setMovies(
        anonymousProfile.onboarding_completed
          ? await getRecommendations(visitorToken)
          : [],
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "로그아웃하지 못했습니다.");
    }
  }

  if (isBooting) {
    return <main className="app-shell"><div className="loading-card">저장된 취향을 확인하고 있어요…</div></main>;
  }

  const needsOnboarding = !profile?.onboarding_completed || isEditingTaste;

  return (
    <main className="app-shell">
      <nav className="topbar" aria-label="사용자 메뉴">
        <div className="brand">MOODPICK</div>
        {authSession ? (
          <div className="account-menu">
            <span><strong>{authSession.user.nickname}</strong>님의 취향을 동기화 중</span>
            <button type="button" onClick={handleLogout}>로그아웃</button>
          </div>
        ) : (
          <button className="secondary-button" type="button" onClick={() => setIsAuthOpen(true)}>
            로그인 · 회원가입
          </button>
        )}
      </nav>
      <header className="hero">
        <h1>오늘 마음에 맞는 영화,<br />취향을 기억해서 골라드려요.</h1>
        <p>
          영화 정보는 TMDB에서 새롭게, 나의 취향과 반응은 안전하게 기억합니다.
          {!authSession && " 로그인하면 다른 기기에서도 이어볼 수 있어요."}
        </p>
      </header>

      {error && <div className="error-banner" role="alert">{error}</div>}

      {isAuthOpen && (
        <AuthPanel
          visitorToken={visitorToken}
          onAuthenticated={handleAuthenticated}
          onClose={() => setIsAuthOpen(false)}
        />
      )}

      {needsOnboarding ? (
        <OnboardingForm
          initialGenres={profile?.favorite_genres}
          initialMoods={profile?.moods}
          onComplete={handleOnboarding}
        />
      ) : (
        <>
          <div className="taste-summary">
            <div>
              <span>기억 중인 취향</span>
              <strong>{profile.favorite_genres.join(" · ")}</strong>
            </div>
            <button type="button" onClick={() => setIsEditingTaste(true)}>취향 수정</button>
          </div>
          <RecommendationGrid
            movies={movies}
            isRefreshing={isRefreshing}
            onFeedback={handleFeedback}
            onRefresh={refreshRecommendations}
          />
          <details className="chat-panel">
            <summary>영화 데이터에 대해 더 물어보기</summary>
            <ChatWindow sessionId={visitorToken} />
          </details>
        </>
      )}
    </main>
  );
}
