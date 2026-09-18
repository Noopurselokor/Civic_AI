"""
Duplicate detection - simplified for the 2-day build.
Checks: same category + within ~30 meters of an existing open report.
(CLIP image-embedding similarity is a documented future enhancement,
skipped here to fit the timeline honestly.)
"""

from math import radians, sin, cos, sqrt, atan2

DUPLICATE_RADIUS_METERS = 30


def haversine_distance(lat1, lng1, lat2, lng2):
    """Straight-line distance between two GPS points, in meters."""
    R = 6371000  # Earth radius in meters
    phi1, phi2 = radians(lat1), radians(lat2)
    d_phi = radians(lat2 - lat1)
    d_lambda = radians(lng2 - lng1)
    a = sin(d_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(d_lambda / 2) ** 2
    return 2 * R * atan2(sqrt(a), sqrt(1 - a))


def find_duplicate(supabase, lat, lng, category):
    """
    Looks for an existing unresolved report of the same category
    within DUPLICATE_RADIUS_METERS. Returns the matching report's id
    if found, else None.
    """
    response = (
        supabase.table("reports")
        .select("id, lat, lng")
        .eq("category", category)
        .neq("status", "resolved")
        .execute()
    )

    for existing in response.data:
        distance = haversine_distance(lat, lng, existing["lat"], existing["lng"])
        if distance <= DUPLICATE_RADIUS_METERS:
            return existing["id"]

    return None
