"use client";

import { useState } from "react";

import { BookCover } from "@/features/chat/BookCover";
import { BookDetailModal } from "@/features/chat/BookDetailModal";
import type { BookRecommendation } from "@/features/chat/types";

interface LikedBooksGridProps {
  books: BookRecommendation[];
  isLoading: boolean;
}

function bookKey(book: BookRecommendation): string {
  return book.isbn || `${book.title}:${book.author || ""}`;
}

export function LikedBooksGrid({ books, isLoading }: LikedBooksGridProps) {
  const [selectedBook, setSelectedBook] = useState<BookRecommendation | null>(null);

  if (isLoading) return <div className="loading-card">좋아요한 책을 불러오고 있어요…</div>;

  return (
    <section aria-labelledby="liked-books-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">나의 책 보관함</p>
          <h2 id="liked-books-title">좋아요한 책</h2>
          <p className="section-description">추천에서 마음에 든 책을 최신순으로 모았어요.</p>
        </div>
      </div>
      {books.length === 0 ? (
        <div className="empty-state">
          <p>아직 좋아요한 책이 없어요.</p>
          <span>책 추천 카드에서 마음에 드는 책을 저장해 보세요.</span>
        </div>
      ) : (
        <div className="liked-books-grid">
          {books.map((book) => (
            <button
              className="liked-book-card"
              key={bookKey(book)}
              type="button"
              onClick={() => setSelectedBook(book)}
              aria-label={`${book.title} 상세 정보 보기`}
            >
              <span className="liked-book-cover"><BookCover book={book} /></span>
              <span>
                <strong>{book.title}</strong>
                <small>{book.author || "저자 미상"}</small>
                <em>{[book.publisher, book.pub_year].filter(Boolean).join(" · ")}</em>
              </span>
            </button>
          ))}
        </div>
      )}
      {selectedBook && <BookDetailModal book={selectedBook} onClose={() => setSelectedBook(null)} />}
    </section>
  );
}
