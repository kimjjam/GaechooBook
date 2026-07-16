"use client";

import { useEffect, useRef, useState } from "react";

import type { BookRecommendation } from "@/features/chat/types";

interface ChatBookCardsProps {
  books: BookRecommendation[];
}

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

function BookCover({ book, large = false }: { book: BookRecommendation; large?: boolean }) {
  if (book.thumbnail_url) {
    return (
      // 도서 API마다 이미지 호스트가 달라 Next Image의 고정 호스트 목록을 사용할 수 없다.
      // eslint-disable-next-line @next/next/no-img-element
      <img src={book.thumbnail_url} alt={`${book.title} 표지`} loading="lazy" />
    );
  }

  return <span className={large ? "book-cover-placeholder large" : "book-cover-placeholder"}>BOOK</span>;
}

function BookDetailModal({ book, onClose }: BookDetailModalProps) {
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

export function ChatBookCards({ books }: ChatBookCardsProps) {
  const [selectedBook, setSelectedBook] = useState<BookRecommendation | null>(null);
  const visibleBooks = books.slice(0, 5);

  return (
    <>
      <div className="chat-book-cards" aria-label="추천 도서 카드">
        {visibleBooks.map((book, index) => (
          <button
            className="chat-book-card"
            key={`${book.isbn || book.title}-${index}`}
            type="button"
            onClick={() => setSelectedBook(book)}
            aria-label={`${book.title} 상세 정보 보기`}
          >
            <span className="chat-book-cover"><BookCover book={book} /></span>
            <span className="chat-book-copy">
              <strong>{book.title}</strong>
              <small>{book.author || "저자 미상"}</small>
              <em>{book.recommendation_reason || [book.publisher, book.pub_year].filter(Boolean).join(" · ") || book.sources.join(" · ")}</em>
              <span className="book-source-badge">출처 {book.sources.join(" · ")}</span>
            </span>
          </button>
        ))}
      </div>
      {selectedBook && <BookDetailModal book={selectedBook} onClose={() => setSelectedBook(null)} />}
    </>
  );
}
