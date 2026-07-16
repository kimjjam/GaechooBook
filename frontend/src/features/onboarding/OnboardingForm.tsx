"use client";

import { useState } from "react";

const GENRES = [
  "액션", "코미디", "드라마", "로맨스", "SF", "판타지",
  "스릴러", "미스터리", "애니메이션", "공포", "다큐멘터리", "가족",
] as const;

const MOODS = [
  "가볍고 유쾌한",
  "따뜻하고 편안한",
  "긴장감 있는",
  "상상력을 자극하는",
  "감동적인",
] as const;

interface OnboardingFormProps {
  initialGenres?: string[];
  initialMoods?: string[];
  onComplete: (input: {
    favoriteGenres: string[];
    moods: string[];
    favoriteMovie: string;
  }) => Promise<void>;
}

function toggleValue(values: string[], value: string, maximum: number): string[] {
  if (values.includes(value)) return values.filter((item) => item !== value);
  if (values.length >= maximum) return values;
  return [...values, value];
}

function normalizeValues(
  values: string[],
  choices: readonly string[],
  maximum: number,
): string[] {
  return [...new Set(values)]
    .filter((value) => choices.includes(value))
    .slice(0, maximum);
}

export function OnboardingForm({
  initialGenres = [],
  initialMoods = [],
  onComplete,
}: OnboardingFormProps) {
  const [genres, setGenres] = useState<string[]>(() =>
    normalizeValues(initialGenres, GENRES, 5),
  );
  const [moods, setMoods] = useState<string[]>(() =>
    normalizeValues(initialMoods, MOODS, 3),
  );
  const [favoriteMovie, setFavoriteMovie] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (genres.length === 0 || isSaving) return;
    setIsSaving(true);
    try {
      await onComplete({ favoriteGenres: genres, moods, favoriteMovie });
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <section className="onboarding-card" aria-labelledby="onboarding-title">
      <p className="eyebrow">30초 취향 설정</p>
      <h2 id="onboarding-title">어떤 영화를 좋아하세요?</h2>
      <p className="section-description">
        선택한 취향은 이 브라우저의 방문자 ID와 함께 저장되어 다음 방문에도 이어집니다.
      </p>

      <form onSubmit={handleSubmit}>
        <fieldset>
          <legend>좋아하는 장르 <span>최대 5개</span></legend>
          <div className="choice-grid">
            {GENRES.map((genre) => (
              <button
                key={genre}
                type="button"
                className={genres.includes(genre) ? "choice selected" : "choice"}
                aria-pressed={genres.includes(genre)}
                onClick={() => setGenres((current) => toggleValue(current, genre, 5))}
              >
                {genre}
              </button>
            ))}
          </div>
        </fieldset>

        <fieldset>
          <legend>오늘 끌리는 분위기 <span>최대 3개</span></legend>
          <div className="choice-grid mood-grid">
            {MOODS.map((mood) => (
              <button
                key={mood}
                type="button"
                className={moods.includes(mood) ? "choice selected" : "choice"}
                aria-pressed={moods.includes(mood)}
                onClick={() => setMoods((current) => toggleValue(current, mood, 3))}
              >
                {mood}
              </button>
            ))}
          </div>
        </fieldset>

        <label className="text-field">
          인생 영화가 있다면 알려주세요 <span>선택</span>
          <input
            value={favoriteMovie}
            onChange={(event) => setFavoriteMovie(event.target.value)}
            placeholder="예: 인터스텔라"
            maxLength={200}
          />
        </label>

        <button className="primary-button" type="submit" disabled={genres.length === 0 || isSaving}>
          {isSaving ? "취향 저장 중..." : "내 취향 영화 추천받기"}
        </button>
      </form>
    </section>
  );
}
