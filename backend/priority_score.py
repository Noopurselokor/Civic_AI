"""Transparent priority scoring formula."""

def calculate_priority(confidence, duplicate_count, days_open, location_weight):
    normalized_duplicates = min(duplicate_count / 10, 1.0)
    normalized_days = min(days_open / 30, 1.0)
    return round(
        0.4 * confidence
        + 0.3 * normalized_duplicates
        + 0.2 * normalized_days
        + 0.1 * location_weight,
        3
    )
