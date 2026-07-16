"use client";

import Image from "next/image";
import { useState } from "react";

import { MovieDetailModal } from "@/features/chat/MovieDetailModal";
import type { MovieRecommendation } from "@/features/chat/types";

interface ChatMovieCardsProps {
  movies: MovieRecommendation[];
  onLike?: (movie: MovieRecommendation) => void;
}

export function ChatMovieCards({ movies, onLike }: ChatMovieCardsProps) {
  const [selectedMovieId, setSelectedMovieId] = useState<number | null>(null);
  const [likedMovieIds, setLikedMovieIds] = useState<Set<number>>(() => new Set());

  function handleLike(movie: MovieRecommendation) {
    setLikedMovieIds((current) => new Set(current).add(movie.id));
    onLike?.(movie);
  }

  return (
    <>
      <div className="chat-movie-cards" aria-label="추천 영화 카드">
        {movies.map((movie) => (
          <article
            className="chat-movie-card"
            key={movie.id}
          >
            <button
              className="chat-card-main"
              type="button"
              onClick={() => setSelectedMovieId(movie.id)}
              aria-label={`${movie.title} 상세 정보 보기`}
            >
              <span className="chat-movie-poster">
                {movie.poster_url ? (
                  <Image src={movie.poster_url} alt="" fill sizes="150px" className="poster-image" />
                ) : (
                  <span>MoodPick</span>
                )}
                <span className="chat-movie-rating">★ {movie.rating.toFixed(1)}</span>
              </span>
              <span className="chat-movie-copy">
                <strong>{movie.title}</strong>
                <small>{movie.release_year ?? "연도 미상"} · {movie.genres.slice(0, 2).join(" · ")}</small>
                <em>{movie.reason}</em>
              </span>
            </button>
            <button
              className="chat-card-like"
              type="button"
              onClick={() => handleLike(movie)}
              disabled={likedMovieIds.has(movie.id)}
              aria-label={`${movie.title} 취향에 저장`}
            >
              {likedMovieIds.has(movie.id) ? "✓ 저장됨" : "♡ 취향이에요"}
            </button>
          </article>
        ))}
      </div>
      {selectedMovieId !== null && (
        <MovieDetailModal movieId={selectedMovieId} onClose={() => setSelectedMovieId(null)} />
      )}
    </>
  );
}
