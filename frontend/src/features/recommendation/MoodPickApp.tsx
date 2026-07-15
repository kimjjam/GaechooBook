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
const CARD_RATING_TARGET = 10;
type ContentType = "movies" | "books";
type MovieView = "cards" | "chat";
type GenreSignals = Record<string, number>;

function getVisitorToken(): string {
  const stored = localStorage.getItem(VISITOR_TOKEN_KEY);
  if (stored) return stored;
  const token = crypto.randomUUID();
  localStorage.setItem(VISITOR_TOKEN_KEY, token);
  return token;
}

function joinGenres(genres: string[]): string {
  return genres.length > 1 ? `${genres[0]}와 ${genres[1]}` : genres[0] ?? "새로운 장르";
}

function buildMovieOpeningMessage(
  savedGenres: string[],
  genreSignals: GenreSignals,
): string {
  const rankedSignals = Object.entries(genreSignals).sort((a, b) => b[1] - a[1]);
  const likedGenres = rankedSignals.filter(([, score]) => score > 0).slice(0, 2).map(([genre]) => genre);
  const lessPreferredGenre = rankedSignals.filter(([, score]) => score < 0).at(-1)?.[0];
  const fallbackGenres = savedGenres.filter((genre) => genre !== lessPreferredGenre).slice(0, 2);
  const highlightedGenres = likedGenres.length > 0 ? likedGenres : fallbackGenres;

  if (highlightedGenres.length > 0 && lessPreferredGenre) {
    return `방금 평가를 보니 ${joinGenres(highlightedGenres)} 쪽에 마음이 가고, ${lessPreferredGenre} 장르는 오늘 조금 덜 끌리셨네요. 지금은 어떤 분위기의 영화를 보고 싶으세요?`;
  }
  if (highlightedGenres.length > 0) {
    return `10편의 평가를 보니 ${joinGenres(highlightedGenres)} 취향이 두드러져요. 지금은 가볍게 볼 작품과 깊이 몰입할 작품 중 어느 쪽이 끌리세요?`;
  }
  return "10편의 반응이 꽤 다양하네요. 오늘은 익숙한 취향과 새로운 장르 중 어느 쪽을 탐색해 볼까요?";
}

export function MoodPickApp() {
  const [visitorToken, setVisitorToken] = useState("");
  const [profile, setProfile] = useState<TasteProfile | null>(null);
  const [authSession, setAuthSession] = useState<AuthSession | null>(null);
  const [contentType, setContentType] = useState<ContentType | null>(null);
  const [movies, setMovies] = useState<MovieRecommendation[]>([]);
  const [seenMovieIds, setSeenMovieIds] = useState<number[]>([]);
  const [movieView, setMovieView] = useState<MovieView>("cards");
  const [ratedMovieCount, setRatedMovieCount] = useState(0);
  const [genreSignals, setGenreSignals] = useState<GenreSignals>({});
  const [movieOpeningMessage, setMovieOpeningMessage] = useState("");
  const [isBooting, setIsBooting] = useState(true);
  const [isContentLoading, setIsContentLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isEditingTaste, setIsEditingTaste] = useState(false);
  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function showMovies(nextMovies: MovieRecommendation[], resetSeen = false) {
    setMovies(nextMovies);
    setSeenMovieIds((previous) => [
      ...new Set([...(resetSeen ? [] : previous), ...nextMovies.map((movie) => movie.id)]),
    ]);
  }

  useEffect(() => {
    let cancelled = false;
    const token = getVisitorToken();
    setVisitorToken(token);

    async function restoreSession() {
      try {
        const restoredSession = await getAuthSession();
        if (cancelled) return;
        setAuthSession(restoredSession);
      } catch (caught) {
        if (!cancelled) setError(caught instanceof Error ? caught.message : "서비스를 불러오지 못했습니다.");
      } finally {
        if (!cancelled) setIsBooting(false);
      }
    }

    void restoreSession();
    return () => {
      cancelled = true;
    };
  }, []);

  async function loadMovieExperience() {
    if (!visitorToken) return;
    setIsContentLoading(true);
    setError(null);
    try {
      const restoredProfile = await getProfile(visitorToken);
      setProfile(restoredProfile);
      const nextMovies = restoredProfile.onboarding_completed
        ? await getRecommendations(visitorToken)
        : [];
      showMovies(nextMovies, true);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "영화 추천을 불러오지 못했습니다.");
    } finally {
      setIsContentLoading(false);
    }
  }

  function handleContentSelect(selected: ContentType) {
    setContentType(selected);
    setError(null);
    window.scrollTo({ top: 0 });
    if (selected === "movies") {
      setMovieView("cards");
      setRatedMovieCount(0);
      setSeenMovieIds([]);
      setGenreSignals({});
      setMovieOpeningMessage("");
      void loadMovieExperience();
    }
  }

  function handleBackToPicker() {
    setContentType(null);
    setError(null);
    window.scrollTo({ top: 0 });
  }

  async function refreshRecommendations() {
    if (!visitorToken) return;
    setIsRefreshing(true);
    setError(null);
    try {
      const nextMovies = await getRecommendations(visitorToken, seenMovieIds);
      if (nextMovies.length === 0) {
        throw new Error("새로 보여드릴 영화를 모두 살펴봤어요. 취향을 조금 바꾸거나 카드를 평가해 주세요.");
      }
      showMovies(nextMovies);
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
      setMovieView("cards");
      setRatedMovieCount(0);
      setGenreSignals({});
      setMovieOpeningMessage("");
      showMovies(await getRecommendations(visitorToken), true);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "취향을 저장하지 못했습니다.");
      throw caught;
    }
  }

  async function handleFeedback(movie: MovieRecommendation, action: "liked" | "disliked") {
    setError(null);
    try {
      await sendFeedback(visitorToken, movie, action, authSession?.csrf_token);
      const nextCount = ratedMovieCount + 1;
      const signalDelta = action === "liked" ? 1 : -1;
      const nextGenreSignals = { ...genreSignals };
      for (const genre of movie.genres) {
        nextGenreSignals[genre] = (nextGenreSignals[genre] ?? 0) + signalDelta;
      }
      setRatedMovieCount(nextCount);
      setGenreSignals(nextGenreSignals);
      if (nextCount >= CARD_RATING_TARGET) {
        setMovieOpeningMessage(
          buildMovieOpeningMessage(profile?.favorite_genres ?? [], nextGenreSignals),
        );
        setMovieView("chat");
        window.scrollTo({ top: 0 });
        return;
      }
      try {
        const remainingMovies = movies.filter((candidate) => candidate.id !== movie.id);
        const replacements = await getRecommendations(visitorToken, seenMovieIds);
        const replacement = replacements[0];
        showMovies(replacement ? [...remainingMovies, replacement] : remainingMovies);
      } catch (caught) {
        setError(caught instanceof Error ? `평가는 저장했지만 새 추천을 불러오지 못했습니다: ${caught.message}` : "평가는 저장했지만 새 추천을 불러오지 못했습니다.");
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "평가를 저장하지 못했습니다.");
    }
  }

  async function handleShowMovieCards() {
    setMovieView("cards");
    setRatedMovieCount(0);
    setGenreSignals({});
    setMovieOpeningMessage("");
    window.scrollTo({ top: 0 });
    await refreshRecommendations();
  }

  async function handleAuthenticated(session: AuthSession) {
    setAuthSession(session);
    setIsAuthOpen(false);
    setError(null);
    if (contentType === "movies") {
      await loadMovieExperience();
      setIsEditingTaste(false);
    }
  }

  async function handleLogout() {
    if (!authSession) return;
    setError(null);
    try {
      await logout(authSession.csrf_token);
      setAuthSession(null);
      if (contentType === "movies") await loadMovieExperience();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "로그아웃하지 못했습니다.");
    }
  }

  if (isBooting) {
    return <main className="app-shell"><div className="loading-card">서비스를 준비하고 있어요…</div></main>;
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

      {error && <div className="error-banner" role="alert">{error}</div>}

      {isAuthOpen && (
        <AuthPanel
          visitorToken={visitorToken}
          onAuthenticated={handleAuthenticated}
          onClose={() => setIsAuthOpen(false)}
        />
      )}

      {!contentType ? (
        <section className="content-picker" aria-labelledby="content-picker-title">
          <div className="picker-copy">
            <p className="eyebrow">오늘의 추천</p>
            <h1 id="content-picker-title">지금은 무엇을<br />만나고 싶나요?</h1>
            <p>보고 싶은 이야기와 읽고 싶은 이야기 중 하나를 골라주세요.</p>
          </div>
          <div className="content-options">
            <button className="content-option movie-option" type="button" onClick={() => handleContentSelect("movies")}>
              <span className="option-number">01</span>
              <span className="option-icon" aria-hidden="true">▶</span>
              <span className="option-title">영화</span>
              <span className="option-description">취향과 기분에 맞는 영화를 골라드려요.</span>
              <span className="option-link">영화 추천 받기 <span aria-hidden="true">→</span></span>
            </button>
            <button className="content-option book-option" type="button" onClick={() => handleContentSelect("books")}>
              <span className="option-number">02</span>
              <span className="option-icon" aria-hidden="true">▤</span>
              <span className="option-title">도서</span>
              <span className="option-description">관심사와 지금의 마음에 맞는 책을 찾아드려요.</span>
              <span className="option-link">도서 추천 받기 <span aria-hidden="true">→</span></span>
            </button>
          </div>
        </section>
      ) : contentType === "books" ? (
        <>
          <header className="hero content-hero">
            <button className="back-button" type="button" onClick={handleBackToPicker}>← 영화 · 도서 다시 선택</button>
            <h1>지금 마음에 맞는 책,<br />함께 찾아드릴게요.</h1>
            <p>여러 도서 검색 결과를 한곳에서 비교해 추천합니다.</p>
          </header>
          <section className="book-recommendation-panel" aria-label="도서 추천 대화">
            <ChatWindow sessionId={visitorToken} mode="books" />
          </section>
        </>
      ) : isContentLoading ? (
        <div className="loading-card content-loading">영화 취향을 불러오고 있어요…</div>
      ) : (
        <>
          <header className="hero content-hero">
            <button className="back-button" type="button" onClick={handleBackToPicker}>← 영화 · 도서 다시 선택</button>
            <h1>오늘 마음에 맞는 영화,<br />취향을 기억해서 골라드려요.</h1>
            <p>
              영화 정보는 TMDB에서 새롭게, 나의 취향과 반응은 안전하게 기억합니다.
              {!authSession && " 로그인하면 다른 기기에서도 이어볼 수 있어요."}
            </p>
          </header>
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
          {movieView === "cards" ? (
            <RecommendationGrid
              movies={movies}
              isRefreshing={isRefreshing}
              ratedCount={ratedMovieCount}
              ratingTarget={CARD_RATING_TARGET}
              onFeedback={handleFeedback}
              onRefresh={refreshRecommendations}
            />
          ) : (
            <section className="movie-chat-experience" aria-labelledby="movie-chat-title">
              <div className="section-heading movie-chat-heading">
                <div>
                  <p className="eyebrow">대화로 더 정확하게</p>
                  <h2 id="movie-chat-title">이제 편하게 말씀해 주세요</h2>
                  <p className="section-description">카드에서 배운 취향과 지금의 요청을 함께 반영해 추천할게요.</p>
                </div>
              </div>
              <div className="movie-chat-window">
                <ChatWindow
                  sessionId={visitorToken}
                  mode="movies"
                  initialAssistantMessage={movieOpeningMessage}
                />
              </div>
              <button className="secondary-button card-return-button" type="button" onClick={() => void handleShowMovieCards()}>
                영화 카드 다시 보기
              </button>
            </section>
          )}
            </>
          )}
        </>
      )}
    </main>
  );
}
