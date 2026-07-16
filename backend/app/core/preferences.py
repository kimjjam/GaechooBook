PREFERRED_GENRE_MIN_WEIGHT = 0.5


def preferred_genres(genre_weights: dict[str, float]) -> list[str]:
    """Return genres backed by meaningful positive preference evidence."""
    return [
        genre
        for genre, weight in genre_weights.items()
        if float(weight) >= PREFERRED_GENRE_MIN_WEIGHT
    ]


def updated_genre_weight(current_weight: float | None, action: str) -> float:
    """Apply feedback without treating an unseen genre as already preferred."""
    if action not in {"liked", "disliked"}:
        raise ValueError(f"Unsupported feedback action: {action}")
    delta = 0.2 if action == "liked" else -0.15
    base_weight = float(current_weight) if current_weight is not None else 0.0
    return round(max(-2.0, min(2.0, base_weight + delta)), 3)
