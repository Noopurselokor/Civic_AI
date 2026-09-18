"""Reverse geocoding via Nominatim."""
import requests

def reverse_geocode(lat: float, lng: float) -> str:
    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lng, "format": "json", "zoom": 17, "addressdetails": 1},
            headers={"User-Agent": "CivicAI/1.0"},
            timeout=5
        )
        response.raise_for_status()
        addr = response.json().get("address", {})

        parts = [
            addr.get("amenity") or addr.get("shop") or addr.get("building"),
            addr.get("road") or addr.get("pedestrian") or addr.get("footway") or addr.get("path"),
            addr.get("neighbourhood") or addr.get("suburb") or addr.get("quarter"),
            addr.get("city") or addr.get("town") or addr.get("village"),
            addr.get("state"),
        ]
        result = ", ".join(p for p in parts if p)
        return result if result else f"{lat:.5f}, {lng:.5f}"
    except Exception:
        return f"{lat:.5f}, {lng:.5f}"
