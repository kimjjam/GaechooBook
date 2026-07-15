import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "무드픽 (MoodPick)",
  description: "오늘의 취향과 기분에 맞는 영화와 도서를 추천하는 서비스",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
