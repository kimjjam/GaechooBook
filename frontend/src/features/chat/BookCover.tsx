import type { BookRecommendation } from "@/features/chat/types";

interface BookCoverProps {
  book: BookRecommendation;
  large?: boolean;
}

export function BookCover({ book, large = false }: BookCoverProps) {
  if (book.thumbnail_url) {
    return (
      // 도서 API마다 이미지 호스트가 달라 Next Image의 고정 호스트 목록을 사용할 수 없다.
      // eslint-disable-next-line @next/next/no-img-element
      <img src={book.thumbnail_url} alt={`${book.title} 표지`} loading="lazy" />
    );
  }

  return <span className={large ? "book-cover-placeholder large" : "book-cover-placeholder"}>BOOK</span>;
}
