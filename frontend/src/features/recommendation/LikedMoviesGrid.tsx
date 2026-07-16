"use client";

import Image from "next/image";
import { useState } from "react";

import { MovieDetailModal } from "@/features/chat/MovieDetailModal";
import type { MovieRecommendation } from "@/features/chat/types";

interface LikedMoviesGridProps {
  movies: MovieRecommendation[];
  isLoading: boolean;
}

export function LikedMoviesGrid({ movies, isLoading }: LikedMoviesGridProps) {
  const [selectedMovieId, setSelectedMovieId] = useState<number | null>(null);

  return (
    <section aria-labelledby="liked-movies-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">나의 영화 보관함</p>
          <h2 id="liked-movies-title">좋아요한 영화</h2>
          <p className="section-description">카드에서 좋아요를 누른 영화를 최신순으로 모았어요.</p>
        </div>
      </div>

      {isLoading ? (
        <div className="loading-card">좋아요한 영화를 불러오고 있어요…</div>
      ) : movies.length === 0 ? (
        <div className="empty-state">
          <p>아직 좋아요한 영화가 없어요.</p>
          <span>영화 카드에서 마음에 드는 작품에 좋아요를 눌러 보세요.</span>
        </div>
      ) : (
        <div className="movie-grid">
          {movies.map((movie) => (
            <button
              className="movie-card liked-movie-card"
              key={movie.id}
              type="button"
              onClick={() => setSelectedMovieId(movie.id)}
              aria-label={`${movie.title} 상세 정보 보기`}
            >
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
                {movie.rating > 0 && <span className="rating">★ {movie.rating.toFixed(1)}</span>}
              </div>
              <span className="movie-content">
                <strong>{movie.title}</strong>
                <span className="movie-meta">
                  {movie.release_year ?? "연도 미상"} · {movie.genres.slice(0, 2).join(" · ")}
                </span>
              </span>
            </button>
          ))}
        </div>
      )}

      {selectedMovieId !== null && (
        <MovieDetailModal movieId={selectedMovieId} onClose={() => setSelectedMovieId(null)} />
      )}
    </section>
  );
}
