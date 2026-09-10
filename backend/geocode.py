"""Reverse geocoding via Nominatim (free, no API key needed for low volume)."""
import requests

def reverse_geocode(lat: float, lng: float) -> str:
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {"lat": lat, "lon": lng, "format": "json"}
    headers = {"User-Agent": "CivicAI/1.0"}  # required by Nominatim's usage policy
    response = requests.get(url, params=params, headers=headers)
    return response.json().get("display_name", "Unknown location")
