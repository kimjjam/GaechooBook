"use client";

import { useEffect, useRef, useState } from "react";
import { ChatMovieCards } from "@/features/chat/ChatMovieCards";
import { ChatBookCards } from "@/features/chat/ChatBookCards";
import { sendChatMessage } from "@/lib/api/chatClient";
import type { BookPreferences } from "@/lib/api/chatClient";
import type { BookRecommendation, ChatMessage, MovieRecommendation } from "@/features/chat/types";

interface ChatWindowProps {
  sessionId: string;
  mode?: "general" | "movies" | "books";
  initialAssistantMessage?: string;
  excludedMovieIds?: number[];
  onMoviesRecommended?: (movies: MovieRecommendation[]) => void;
}

interface BookBasicProfile {
  age_group: string;
  gender: string;
  mbti: string;
}

type BookFlowPhase = "loading" | "profile" | "confirm" | "taste" | "ready";

const BOOK_PROFILE_STORAGE_KEY_PREFIX = "moodpick_book_basic_profile";

const BOOK_PROFILE_QUESTIONS = [
  {
    prompt: "먼저 기본정보를 확인할게요. 어느 연령대인가요?",
    options: ["초등학생", "중학생", "고등학생", "20대", "30대", "40대", "50대 이상"],
  },
  {
    prompt: "성별도 선택해 주세요.",
    options: ["여성", "남성", "논바이너리", "응답하지 않음"],
  },
  {
    prompt: "마지막으로 MBTI를 알려주세요. 독서 취향을 넓히는 보조 신호로만 사용할게요.",
    options: [
      "ISTJ", "ISFJ", "INFJ", "INTJ",
      "ISTP", "ISFP", "INFP", "INTP",
      "ESTP", "ESFP", "ENFP", "ENTP",
      "ESTJ", "ESFJ", "ENFJ", "ENTJ",
    ],
  },
];

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
    prompt: "이번에는 어떤 느낌으로 읽고 싶나요?",
    options: ["가볍고 편하게", "깊이 생각하며", "빠르게 몰입해서", "따뜻하게 쉬면서"],
  },
];

function getBookProfileStorageKey(sessionId: string) {
  return `${BOOK_PROFILE_STORAGE_KEY_PREFIX}:${sessionId}`;
}

function isBookBasicProfile(value: unknown): value is BookBasicProfile {
  if (!value || typeof value !== "object") return false;
  const profile = value as Record<string, unknown>;
  return typeof profile.age_group === "string"
    && BOOK_PROFILE_QUESTIONS[0].options.includes(profile.age_group)
    && typeof profile.gender === "string"
    && BOOK_PROFILE_QUESTIONS[1].options.includes(profile.gender)
    && typeof profile.mbti === "string"
    && BOOK_PROFILE_QUESTIONS[2].options.includes(profile.mbti);
}

function getStoredBookProfile(sessionId: string): BookBasicProfile | null {
  try {
    const stored = localStorage.getItem(getBookProfileStorageKey(sessionId));
    if (!stored) return null;
    const parsed: unknown = JSON.parse(stored);
    return isBookBasicProfile(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

function saveStoredBookProfile(sessionId: string, profile: BookBasicProfile) {
  try {
    localStorage.setItem(getBookProfileStorageKey(sessionId), JSON.stringify(profile));
  } catch {
    // 저장소를 사용할 수 없는 환경에서도 현재 대화의 추천은 계속 진행한다.
  }
}

function removeStoredBookProfile(sessionId: string) {
  try {
    localStorage.removeItem(getBookProfileStorageKey(sessionId));
  } catch {
    // 저장소를 사용할 수 없는 환경에서는 현재 대화 상태만 초기화한다.
  }
}

function describeBookProfile(profile: BookBasicProfile) {
  if (profile.gender === "응답하지 않음") {
    return `사용자분은 ${profile.age_group} ${profile.mbti}이며, 성별은 응답하지 않으셨습니다. 이대로 찾아드릴까요?`;
  }
  return `사용자분의 정보는 ${profile.age_group} ${profile.mbti} ${profile.gender}이십니다. 이대로 찾아드릴까요?`;
}

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
    const openingMessage = initialAssistantMessage ?? "";
    return openingMessage
      ? [{ id: "initial-assistant-message", role: "assistant", text: openingMessage }]
      : [];
  });
  const [bookFlowPhase, setBookFlowPhase] = useState<BookFlowPhase>(mode === "books" ? "loading" : "ready");
  const [bookProfileStep, setBookProfileStep] = useState(0);
  const [bookProfileAnswers, setBookProfileAnswers] = useState<string[]>([]);
  const [bookBasicProfile, setBookBasicProfile] = useState<BookBasicProfile | null>(null);
  const [bookTasteStep, setBookTasteStep] = useState(0);
  const [bookTasteAnswers, setBookTasteAnswers] = useState<string[]>([]);
  const [bookPreferences, setBookPreferences] = useState<BookPreferences | null>(null);
  const [input, setInput] = useState("");
  const [recommendationContext, setRecommendationContext] = useState<Record<string, unknown> | null>(null);
  const [recommendedMovieIds, setRecommendedMovieIds] = useState<number[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (mode !== "books" || !sessionId) return;

    const storedProfile = getStoredBookProfile(sessionId);
    setBookProfileStep(0);
    setBookProfileAnswers([]);
    setBookTasteStep(0);
    setBookTasteAnswers([]);
    setBookPreferences(null);
    setBookBasicProfile(storedProfile);
    setBookFlowPhase("taste");
    setMessages([{
      id: crypto.randomUUID(),
      role: "assistant",
      text: BOOK_TASTE_QUESTIONS[0].prompt,
    }]);
  }, [mode, sessionId]);

  useEffect(() => {
    const history = chatHistoryRef.current;
    if (history) history.scrollTop = history.scrollHeight;
  }, [messages, bookFlowPhase, bookProfileStep, bookTasteStep, isLoading, error]);

  async function sendMessage(text: string) {
    if (!text || isLoading) return;

    const userMessage: ChatMessage = { id: crypto.randomUUID(), role: "user", text };
    setInput("");
    setError(null);

    let requestText = text;
    let nextBookPreferences: BookPreferences | null = null;
    if (mode === "books" && bookFlowPhase === "loading") return;

    if (mode === "books" && bookFlowPhase === "confirm") {
      const normalizedAnswer = text.replace(/\s/g, "");
      if (["예", "네", "좋아요"].includes(normalizedAnswer) && bookBasicProfile) {
        saveStoredBookProfile(sessionId, bookBasicProfile);
        const [genre, topic, readingMood] = bookTasteAnswers;
        nextBookPreferences = {
          genre,
          topic,
          reading_mood: readingMood,
          ...bookBasicProfile,
        };
        setBookPreferences(nextBookPreferences);
        setBookFlowPhase("ready");
        requestText = `책 추천: ${genre}, ${topic}`;
      } else if (["아니오", "아니요", "아뇨"].includes(normalizedAnswer)) {
        removeStoredBookProfile(sessionId);
        setBookBasicProfile(null);
        setBookProfileStep(0);
        setBookProfileAnswers([]);
        setBookFlowPhase("profile");
        setMessages((previous) => [
          ...previous,
          userMessage,
          { id: crypto.randomUUID(), role: "assistant", text: BOOK_PROFILE_QUESTIONS[0].prompt },
        ]);
        return;
      } else {
        setMessages((previous) => [
          ...previous,
          userMessage,
          { id: crypto.randomUUID(), role: "assistant", text: "예 또는 아니오로 답해주세요." },
        ]);
        return;
      }
    }

    if (mode === "books" && bookFlowPhase === "profile") {
      const currentQuestion = BOOK_PROFILE_QUESTIONS[bookProfileStep];
      const normalizedProfileAnswer = bookProfileStep === 2 ? text.toUpperCase() : text;
      if (!currentQuestion.options.includes(normalizedProfileAnswer)) {
        setMessages((previous) => [
          ...previous,
          userMessage,
          { id: crypto.randomUUID(), role: "assistant", text: "아래 선택지 중 하나를 골라주세요." },
        ]);
        return;
      }

      const nextAnswers = [...bookProfileAnswers, normalizedProfileAnswer];
      const nextStep = bookProfileStep + 1;
      setBookProfileAnswers(nextAnswers);
      setBookProfileStep(nextStep);

      if (nextStep < BOOK_PROFILE_QUESTIONS.length) {
        setMessages((previous) => [
          ...previous,
          userMessage,
          { id: crypto.randomUUID(), role: "assistant", text: BOOK_PROFILE_QUESTIONS[nextStep].prompt },
        ]);
        return;
      }

      const [ageGroup, gender, mbti] = nextAnswers;
      const nextProfile = { age_group: ageGroup, gender, mbti: mbti.toUpperCase() };
      setBookBasicProfile(nextProfile);
      setBookFlowPhase("confirm");
      setMessages((previous) => [
        ...previous,
        userMessage,
        { id: crypto.randomUUID(), role: "assistant", text: describeBookProfile(nextProfile) },
      ]);
      return;
    }

    if (mode === "books" && bookFlowPhase === "taste") {
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
      setBookFlowPhase(bookBasicProfile ? "confirm" : "profile");
      setMessages((previous) => [
        ...previous,
        userMessage,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text: bookBasicProfile
            ? describeBookProfile(bookBasicProfile)
            : BOOK_PROFILE_QUESTIONS[0].prompt,
        },
      ]);
      return;
    } else if (mode === "books" && !nextBookPreferences && !/(책|도서|소설|에세이|자기계발|인문학)/.test(text)) {
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
        mode === "books" ? nextBookPreferences ?? bookPreferences : null,
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

  const activeBookOptions = bookFlowPhase === "confirm"
    ? ["예", "아니오"]
    : bookFlowPhase === "profile"
      ? BOOK_PROFILE_QUESTIONS[bookProfileStep]?.options ?? []
      : bookFlowPhase === "taste"
        ? BOOK_TASTE_QUESTIONS[bookTasteStep]?.options ?? []
        : [];

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
        {mode === "books" && activeBookOptions.length > 0 && !isLoading && (
          <div className="prompt-suggestions chat-quick-replies" aria-label="책 취향 빠른 답변">
            {activeBookOptions.map((option) => (
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
          disabled={isLoading || bookFlowPhase === "loading" || !input.trim()}
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
