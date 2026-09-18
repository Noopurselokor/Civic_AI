"""Transparent priority scoring formula for municipal triage."""


def calculate_priority(
    confidence,
    duplicate_count,
    days_open,
    location_weight,
    severity_score=0.5,
    sentiment_score=0.0,
):
    """Return a 0-1 score while keeping every input explainable to admins."""
    normalized_duplicates = min(duplicate_count / 10, 1.0)
    normalized_days = min(days_open / 30, 1.0)
    # Negative sentiment slightly increases attention, but urgency/severity has
    # substantially more influence than emotional wording alone.
    negative_sentiment = max(-sentiment_score, 0.0)
    return round(
        0.30 * confidence
        + 0.20 * normalized_duplicates
        + 0.15 * normalized_days
        + 0.10 * location_weight
        + 0.20 * severity_score
        + 0.05 * negative_sentiment,
        3
    )
