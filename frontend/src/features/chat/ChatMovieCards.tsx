"use client";

import Image from "next/image";
import { useState } from "react";

import { MovieDetailModal } from "@/features/chat/MovieDetailModal";
import type { MovieRecommendation } from "@/features/chat/types";

interface ChatMovieCardsProps {
  movies: MovieRecommendation[];
}

export function ChatMovieCards({ movies }: ChatMovieCardsProps) {
  const [selectedMovieId, setSelectedMovieId] = useState<number | null>(null);

  return (
    <>
      <div className="chat-movie-cards" aria-label="추천 영화 카드">
        {movies.map((movie) => (
          <button
            className="chat-movie-card"
            key={movie.id}
            type="button"
            onClick={() => setSelectedMovieId(movie.id)}
            aria-label={`${movie.title} 상세 정보 보기`}
          >
            <div className="chat-movie-poster">
              {movie.poster_url ? (
                <Image src={movie.poster_url} alt="" fill sizes="150px" className="poster-image" />
              ) : (
                <span>MoodPick</span>
              )}
              <span className="chat-movie-rating">★ {movie.rating.toFixed(1)}</span>
            </div>
            <span className="chat-movie-copy">
              <strong>{movie.title}</strong>
              <small>{movie.release_year ?? "연도 미상"} · {movie.genres.slice(0, 2).join(" · ")}</small>
              <em>{movie.reason}</em>
            </span>
          </button>
        ))}
      </div>
      {selectedMovieId !== null && (
        <MovieDetailModal movieId={selectedMovieId} onClose={() => setSelectedMovieId(null)} />
      )}
    </>
  );
}
