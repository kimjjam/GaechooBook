"use client";

import { useEffect, useRef } from "react";

import { BookCover } from "@/features/chat/BookCover";
import type { BookRecommendation } from "@/features/chat/types";

interface BookDetailModalProps {
  book: BookRecommendation;
  onClose: () => void;
}

function summarizeDescription(description?: string | null): string {
  if (!description) return "등록된 책 소개가 아직 없어요.";
  const normalized = description.replace(/\s+/g, " ").trim();
  if (normalized.length <= 240) return normalized;
  return `${normalized.slice(0, 240).trimEnd()}…`;
}

export function BookDetailModal({ book, onClose }: BookDetailModalProps) {
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeButtonRef.current?.focus();

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [onClose]);

  return (
    <div className="movie-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="book-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="book-modal-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <button ref={closeButtonRef} className="movie-modal-close" type="button" onClick={onClose} aria-label="책 상세 정보 닫기">
          ×
        </button>
        <div className="book-modal-cover"><BookCover book={book} large /></div>
        <div className="book-modal-body">
          <p className="book-modal-eyebrow">{book.genre || "오늘의 추천 도서"}</p>
          <h2 id="book-modal-title">{book.title}</h2>
          <p className="book-modal-author">{book.author || "저자 미상"}</p>
          <div className="movie-detail-meta">
            {book.publisher && <span>{book.publisher}</span>}
            {book.pub_year && <span>{book.pub_year}</span>}
            {book.isbn && <span>ISBN {book.isbn}</span>}
          </div>
          <p className="movie-detail-overview">{summarizeDescription(book.description)}</p>
          <p className="book-modal-sources">정보 제공: {book.sources.join(" · ")}</p>
          {book.link && (
            <a className="book-detail-link" href={book.link} target="_blank" rel="noreferrer">
              서점에서 자세히 보기 <span aria-hidden="true">↗</span>
            </a>
          )}
        </div>
      </section>
    </div>
  );
}
