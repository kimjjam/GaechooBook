"use client";

import { useEffect, useRef, useState } from "react";
import { ChatMovieCards } from "@/features/chat/ChatMovieCards";
import { ChatBookCards } from "@/features/chat/ChatBookCards";
import { sendChatMessage } from "@/lib/api/chatClient";
import type { BookRecommendation, ChatMessage, MovieRecommendation } from "@/features/chat/types";

interface ChatWindowProps {
  sessionId: string;
  mode?: "general" | "movies" | "books";
  initialAssistantMessage?: string;
  excludedMovieIds?: number[];
  onMoviesRecommended?: (movies: MovieRecommendation[]) => void;
}

const BOOK_TASTE_QUESTIONS = [
  {
    prompt: "책 취향부터 천천히 알아볼게요. 평소 어떤 종류의 책을 가장 자주 읽나요?",
    options: ["소설", "에세이", "인문·사회", "과학·기술"],
  },
  {
    prompt: "좋아요. 요즘 가장 관심이 가거나 마음에 필요한 주제는 무엇인가요?",
    options: ["마음의 위로", "새로운 지식", "관계와 사랑", "몰입과 재미"],
  },
  {
    prompt: "마지막으로, 이번에는 어떤 느낌으로 읽고 싶나요?",
    options: ["가볍고 편하게", "깊이 생각하며", "빠르게 몰입해서", "따뜻하게 쉬면서"],
  },
  {
    prompt: "추천에 살짝 참고할 MBTI도 알려주세요. 성격을 단정하지 않고 독서 취향을 넓히는 보조 신호로만 사용할게요.",
    options: [
      "ISTJ", "ISFJ", "INFJ", "INTJ",
      "ISTP", "ISFP", "INFP", "INTP",
      "ESTP", "ESFP", "ENFP", "ENTP",
      "ESTJ", "ESFJ", "ENFJ", "ENTJ",
    ],
  },
];

const MBTI_BOOK_KEYWORDS: Record<string, string> = {
  ISTJ: "현실적이고 체계적인 이야기",
  ISFJ: "따뜻한 관계와 공감",
  INFJ: "깊은 내면과 의미",
  INTJ: "통찰과 전략적 사고",
  ISTP: "실용적인 지식과 탐구",
  ISFP: "감성적인 문장과 위로",
  INFP: "상상력과 섬세한 감정",
  INTP: "새로운 관점과 지적 탐구",
  ESTP: "빠른 전개와 강한 몰입",
  ESFP: "유쾌하고 생생한 이야기",
  ENFP: "영감과 다채로운 가능성",
  ENTP: "발상의 전환과 논쟁적인 주제",
  ESTJ: "목표와 성장을 돕는 실용서",
  ESFJ: "사람과 관계의 따뜻한 이야기",
  ENFJ: "성장과 공감을 이끄는 이야기",
  ENTJ: "리더십과 성취를 다루는 책",
};

const MOVIE_SUGGESTIONS = [
  "오늘은 공포영화 추천해줘",
  "가볍게 웃을 수 있는 영화 추천해줘",
  "몰입감 좋은 SF 영화 추천해줘",
];
const MAX_EXCLUDED_MOVIE_IDS = 500;

export function ChatWindow({
  sessionId,
  mode = "general",
  initialAssistantMessage,
  excludedMovieIds = [],
  onMoviesRecommended,
}: ChatWindowProps) {
  const chatHistoryRef = useRef<HTMLDivElement>(null);
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    const openingMessage = initialAssistantMessage
      ?? (mode === "books" ? BOOK_TASTE_QUESTIONS[0].prompt : "");
    return openingMessage
      ? [{ id: "initial-assistant-message", role: "assistant", text: openingMessage }]
      : [];
  });
  const [bookTasteStep, setBookTasteStep] = useState(0);
  const [bookTasteAnswers, setBookTasteAnswers] = useState<string[]>([]);
  const [input, setInput] = useState("");
  const [recommendationContext, setRecommendationContext] = useState<Record<string, unknown> | null>(null);
  const [recommendedMovieIds, setRecommendedMovieIds] = useState<number[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const history = chatHistoryRef.current;
    if (history) history.scrollTop = history.scrollHeight;
  }, [messages, bookTasteStep, isLoading, error]);

  async function sendMessage(text: string) {
    if (!text || isLoading) return;

    const userMessage: ChatMessage = { id: crypto.randomUUID(), role: "user", text };
    setInput("");
    setError(null);

    let requestText = text;
    if (mode === "books" && bookTasteStep < BOOK_TASTE_QUESTIONS.length) {
      const nextAnswers = [...bookTasteAnswers, text];
      const nextStep = bookTasteStep + 1;
      setBookTasteAnswers(nextAnswers);
      setBookTasteStep(nextStep);

      if (nextStep < BOOK_TASTE_QUESTIONS.length) {
        setMessages((previous) => [
          ...previous,
          userMessage,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            text: BOOK_TASTE_QUESTIONS[nextStep].prompt,
          },
        ]);
        return;
      }
      const [genre, topic, readingMood, mbti] = nextAnswers;
      requestText = `책 추천: ${genre}, ${topic}, ${readingMood}, ${MBTI_BOOK_KEYWORDS[mbti] || mbti}`;
    } else if (mode === "books" && !/(책|도서|소설|에세이|자기계발|인문학)/.test(text)) {
      requestText = `도서 추천: ${text}`;
    }

    setMessages((previous) => [...previous, userMessage]);
    setIsLoading(true);

    try {
      const response = await sendChatMessage(
        sessionId,
        requestText,
        mode === "movies" ? recommendationContext : null,
        mode === "movies"
          ? [...new Set([...excludedMovieIds, ...recommendedMovieIds])].slice(-MAX_EXCLUDED_MOVIE_IDS)
          : [],
      );
      const nextContext = response.data?.recommendation_context;
      if (mode === "movies" && nextContext && typeof nextContext === "object" && !Array.isArray(nextContext)) {
        setRecommendationContext(nextContext as Record<string, unknown>);
      }
      const movieData = response.data?.movies;
      const responseMovies = Array.isArray(movieData)
        ? movieData as MovieRecommendation[]
        : undefined;
      if (responseMovies && responseMovies.length > 0) {
        setRecommendedMovieIds((current) => [
          ...new Set([...current, ...responseMovies.map((movie) => movie.id)]),
        ].slice(-MAX_EXCLUDED_MOVIE_IDS));
        onMoviesRecommended?.(responseMovies);
      }
      const bookData = response.data?.books;
      const responseBooks = Array.isArray(bookData)
        ? bookData as BookRecommendation[]
        : undefined;
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text: response.reply,
          movies: responseMovies,
          books: responseBooks,
        },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "알 수 없는 오류가 발생했습니다.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    await sendMessage(input.trim());
  }

  return (
    <div className="chat-window">
      <div ref={chatHistoryRef} className="chat-history" aria-live="polite">
        {messages.length === 0 && mode === "movies" && (
          <div className="chat-empty-state">
            <strong>오늘은 어떤 영화가 끌리나요?</strong>
            <span>평소 취향과 달라도 괜찮아요. 오늘의 요청도 가볍게 기억할게요.</span>
            <div className="prompt-suggestions">
              {MOVIE_SUGGESTIONS.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => void sendMessage(suggestion)}
                  disabled={isLoading}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m) => (
          <div key={m.id} className={`chat-message-group ${m.role}`}>
            <div className={`chat-row ${m.role}`}>
              {m.role === "assistant" && <span className="chat-avatar" aria-hidden="true">M</span>}
              <span className="chat-bubble">
                {m.text}
              </span>
            </div>
            {m.role === "assistant" && m.movies && m.movies.length > 0 && (
              <ChatMovieCards movies={m.movies} />
            )}
            {m.role === "assistant" && m.books && m.books.length > 0 && (
              <ChatBookCards books={m.books} />
            )}
          </div>
        ))}
        {mode === "books" && bookTasteStep < BOOK_TASTE_QUESTIONS.length && !isLoading && (
          <div className="prompt-suggestions chat-quick-replies" aria-label="책 취향 빠른 답변">
            {BOOK_TASTE_QUESTIONS[bookTasteStep].options.map((option) => (
              <button key={option} type="button" onClick={() => void sendMessage(option)}>
                {option}
              </button>
            ))}
          </div>
        )}
        {mode === "movies" && initialAssistantMessage && messages.length === 1 && (
          <div className="prompt-suggestions chat-quick-replies" aria-label="빠른 답변">
            {MOVIE_SUGGESTIONS.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                onClick={() => void sendMessage(suggestion)}
                disabled={isLoading}
              >
                {suggestion}
              </button>
            ))}
          </div>
        )}
        {isLoading && (
          <div className="chat-row assistant" aria-label="답변을 작성하고 있어요">
            <span className="chat-avatar" aria-hidden="true">M</span>
            <span className="chat-bubble typing-indicator" aria-hidden="true">
              <i /><i /><i />
            </span>
          </div>
        )}
        {error && <p className="chat-error" role="alert">{error}</p>}
      </div>
      <form onSubmit={handleSubmit} className="chat-composer">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={
            mode === "books"
              ? "예: 비 오는 날 읽을 추리소설 추천해줘"
              : mode === "movies"
                ? "예: 오늘은 공포영화 추천해줘"
                : "메시지를 입력하세요"
          }
        />
        <button
          type="submit"
          className="chat-send-button"
          disabled={isLoading || !input.trim()}
          aria-label="메시지 보내기"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M12 19V5m0 0-6 6m6-6 6 6" />
          </svg>
        </button>
      </form>
    </div>
  );
}
