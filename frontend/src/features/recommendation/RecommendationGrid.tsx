"use client";

import Image from "next/image";

import type { MovieRecommendation } from "@/features/chat/types";

interface RecommendationGridProps {
  movies: MovieRecommendation[];
  isRefreshing: boolean;
  ratedCount: number;
  ratingTarget: number;
  showRatingProgress: boolean;
  onFeedback: (movie: MovieRecommendation, action: "liked" | "disliked") => void;
  onRefresh: () => Promise<void>;
}

export function RecommendationGrid({
  movies,
  isRefreshing,
  ratedCount,
  ratingTarget,
  showRatingProgress,
  onFeedback,
  onRefresh,
}: RecommendationGridProps) {
  return (
    <section aria-labelledby="recommendation-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">오늘의 무드픽</p>
          <h2 id="recommendation-title">취향에 맞춰 골랐어요</h2>
        </div>
        <button className="secondary-button" type="button" onClick={onRefresh} disabled={isRefreshing}>
          {isRefreshing ? "찾는 중..." : "다시 추천"}
        </button>
      </div>

      {showRatingProgress && (
        <div className="rating-progress" aria-live="polite">
          <div>
            <strong>{ratedCount} / {ratingTarget}</strong>
            <span>편 평가</span>
          </div>
          <div className="rating-progress-track" aria-hidden="true">
            <span style={{ width: `${Math.min(100, (ratedCount / ratingTarget) * 100)}%` }} />
          </div>
          <p>{ratingTarget}편을 평가하면 대화 추천으로 자동 전환돼요.</p>
        </div>
      )}

      {movies.length === 0 ? (
        <div className="empty-state">
          <p>아직 보여드릴 새 영화가 없어요.</p>
          <button className="secondary-button" type="button" onClick={onRefresh}>다시 찾아보기</button>
        </div>
      ) : (
        <div className="movie-grid">
          {movies.map((movie) => (
            <article className="movie-card" key={movie.id}>
              <div className="poster-wrap">
                {movie.poster_url ? (
                  <Image
                    src={movie.poster_url}
                    alt={`${movie.title} 포스터`}
                    fill
                    sizes="(max-width: 680px) 50vw, 220px"
                    className="poster-image"
                  />
                ) : (
                  <div className="poster-placeholder">MoodPick</div>
                )}
                <span className="rating">★ {movie.rating.toFixed(1)}</span>
              </div>
              <div className="movie-content">
                <div>
                  <h3>{movie.title}</h3>
                  <p className="movie-meta">
                    {movie.release_year ?? "연도 미상"} · {movie.genres.slice(0, 2).join(" · ")}
                  </p>
                </div>
                <p className="recommendation-reason">{movie.reason}</p>
                <p className="overview">{movie.overview || "한국어 줄거리 정보가 아직 없어요."}</p>
                <div className="feedback-row" aria-label={`${movie.title} 평가`}>
                  <button
                    type="button"
                    disabled={isRefreshing}
                    onClick={() => onFeedback(movie, "liked")}
                    aria-label={`${movie.title} 좋아요`}
                  >
                    👍 MY MOOD
                  </button>
                  <button
                    type="button"
                    disabled={isRefreshing}
                    onClick={() => onFeedback(movie, "disliked")}
                    aria-label={`${movie.title} 싫어요`}
                  >
                    👎 NOT FOR ME
                  </button>
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
