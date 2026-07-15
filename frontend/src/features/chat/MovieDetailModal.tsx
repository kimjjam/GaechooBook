"use client";

import Image from "next/image";
import { useEffect, useRef, useState } from "react";

import type { MovieDetail } from "@/features/chat/types";
import { getMovieDetail } from "@/lib/api/personalizationClient";

interface MovieDetailModalProps {
  movieId: number;
  onClose: () => void;
}

export function MovieDetailModal({ movieId, onClose }: MovieDetailModalProps) {
  const [movie, setMovie] = useState<MovieDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    let cancelled = false;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeButtonRef.current?.focus();

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }

    window.addEventListener("keydown", handleKeyDown);
    void getMovieDetail(movieId)
      .then((detail) => {
        if (!cancelled) setMovie(detail);
      })
      .catch((caught) => {
        if (!cancelled) {
          setError(caught instanceof Error ? caught.message : "영화 정보를 불러오지 못했습니다.");
        }
      });

    return () => {
      cancelled = true;
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [movieId, onClose]);

  return (
    <div className="movie-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="movie-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="movie-modal-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <button ref={closeButtonRef} className="movie-modal-close" type="button" onClick={onClose} aria-label="상세 정보 닫기">
          ×
        </button>
        {!movie && !error && <div className="movie-modal-loading">영화 정보를 불러오고 있어요…</div>}
        {error && <div className="movie-modal-loading" role="alert">{error}</div>}
        {movie && (
          <>
            <div className="movie-modal-visual">
              {movie.backdrop_url ? (
                <Image src={movie.backdrop_url} alt="" fill sizes="min(920px, 94vw)" className="movie-modal-backdrop-image" />
              ) : movie.poster_url ? (
                <Image src={movie.poster_url} alt="" fill sizes="min(920px, 94vw)" className="movie-modal-backdrop-image" />
              ) : null}
              <div className="movie-modal-visual-shade" />
              <div className="movie-modal-heading">
                <span>★ {movie.rating.toFixed(1)}</span>
                <h2 id="movie-modal-title">{movie.title}</h2>
                {movie.tagline && <p>{movie.tagline}</p>}
              </div>
            </div>
            <div className="movie-modal-body">
              <div className="movie-detail-meta">
                <span>{movie.release_year ?? "연도 미상"}</span>
                {movie.runtime && <span>{movie.runtime}분</span>}
                {movie.genres.map((genre) => <span key={genre}>{genre}</span>)}
              </div>
              <p className="movie-detail-overview">{movie.overview || "등록된 줄거리가 아직 없어요."}</p>
              {movie.trailer_url ? (
                <div className="movie-trailer">
                  <iframe
                    src={movie.trailer_url}
                    title={`${movie.title} 예고편`}
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                    allowFullScreen
                  />
                </div>
              ) : (
                <p className="movie-trailer-empty">등록된 예고편이 아직 없어요.</p>
              )}
            </div>
          </>
        )}
      </section>
    </div>
  );
}
