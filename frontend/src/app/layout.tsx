import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "무드픽 (MoodPick)",
  description: "내 취향을 기억하고 TMDB의 영화 중 꼭 맞는 작품을 추천하는 서비스",
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
