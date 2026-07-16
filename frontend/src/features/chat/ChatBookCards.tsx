"use client";

import { useState } from "react";

import { BookCover } from "@/features/chat/BookCover";
import { BookDetailModal } from "@/features/chat/BookDetailModal";
import type { BookRecommendation } from "@/features/chat/types";

interface ChatBookCardsProps {
  books: BookRecommendation[];
  onLike?: (book: BookRecommendation) => void;
}

export function ChatBookCards({ books, onLike }: ChatBookCardsProps) {
  const [selectedBook, setSelectedBook] = useState<BookRecommendation | null>(null);
  const [likedBookKeys, setLikedBookKeys] = useState<Set<string>>(() => new Set());
  const visibleBooks = books.slice(0, 5);

  function bookKey(book: BookRecommendation): string {
    return book.isbn || `${book.title}:${book.author || ""}`;
  }

  function handleLike(book: BookRecommendation) {
    setLikedBookKeys((current) => new Set(current).add(bookKey(book)));
    onLike?.(book);
  }

  return (
    <>
      <div className="chat-book-cards" aria-label="추천 도서 카드">
        {visibleBooks.map((book) => (
          <article
            className="chat-book-card"
            key={bookKey(book)}
          >
            <button
              className="chat-card-main chat-book-card-main"
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
            <button
              className="chat-card-like"
              type="button"
              onClick={() => handleLike(book)}
              disabled={likedBookKeys.has(bookKey(book))}
              aria-label={`${book.title} 좋아요`}
            >
              {likedBookKeys.has(bookKey(book)) ? "✓ 저장됨" : "♡ 이 책 좋아요"}
            </button>
          </article>
        ))}
      </div>
      {selectedBook && <BookDetailModal book={selectedBook} onClose={() => setSelectedBook(null)} />}
    </>
  );
}
