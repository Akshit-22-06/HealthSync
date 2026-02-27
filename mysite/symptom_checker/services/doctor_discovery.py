from __future__ import annotations

import json
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest

from django.conf import settings


def discover_nearby_doctors(
    *, location: str, specialization: str, limit: int = 6
) -> list[dict]:
    provider = (getattr(settings, "DOCTOR_DISCOVERY_PROVIDER", "osm") or "osm").strip().lower()
    if provider == "osm":
        return _discover_osm(location=location, specialization=specialization, limit=limit)
    if provider == "tomtom":
        return _discover_tomtom(location=location, specialization=specialization, limit=limit)
    return _discover_here(location=location, specialization=specialization, limit=limit)


def suggest_locations(query: str, *, limit: int = 6) -> list[str]:
    cleaned = (query or "").strip()
    if len(cleaned) < 2:
        return []
    max_items = max(4, min(limit, 20))
    queries = [
        {"q": cleaned, "countrycodes": "in"},
        {"q": f"{cleaned}, India", "countrycodes": "in"},
        {"q": cleaned},
    ]
    suggestions: list[str] = []
    seen: set[str] = set()
    for query_params in queries:
        params = {
            **query_params,
            "format": "jsonv2",
            "addressdetails": 1,
            "limit": max_items,
        }
        url = "https://nominatim.openstreetmap.org/search?" + urlparse.urlencode(params)
        payload = _fetch_json(url)
        if not isinstance(payload, list):
            continue
        for row in payload:
            label = (row.get("display_name") or "").strip()
            if not label:
                continue
            key = label.lower()
            if key in seen:
                continue
            seen.add(key)
            suggestions.append(label)
            if len(suggestions) >= max_items:
                return suggestions
    return suggestions


def _discover_osm(*, location: str, specialization: str, limit: int) -> list[dict]:
    center = _nominatim_geocode(location)
    if not center:
        return []

    lat, lon = center
    radius_m = max(1000, min(int(getattr(settings, "OSM_SEARCH_RADIUS_METERS", 12000)), 50000))
    keyword = (specialization or "doctor").strip().lower()
    overpass_query = f"""
[out:json][timeout:20];
(
  node(around:{radius_m},{lat},{lon})["amenity"="doctors"];
  node(around:{radius_m},{lat},{lon})["healthcare"="doctor"];
  node(around:{radius_m},{lat},{lon})["amenity"="clinic"];
  node(around:{radius_m},{lat},{lon})["healthcare"="clinic"];
  node(around:{radius_m},{lat},{lon})["healthcare"="hospital"];
);
out body {max(30, min(limit * 8, 100))};
"""
    payload = _fetch_overpass(overpass_query)
    elements = payload.get("elements") or []
    doctors: list[tuple[int, float, dict]] = []
    seen: set[str] = set()
    lat_c, lon_c = lat, lon
    for el in elements:
        tags = el.get("tags") or {}
        name = (tags.get("name") or "").strip() or "Nearby Clinic"
        city = (
            tags.get("addr:city")
            or tags.get("addr:state")
            or location
        )
        spec_hint = (
            tags.get("healthcare:speciality")
            or tags.get("healthcare:speciality:en")
            or tags.get("description")
            or tags.get("healthcare")
            or "General Physician"
        )
        key = f"{name.lower()}|{city.lower()}"
        if key in seen:
            continue
        text_blob = " ".join(
            [name.lower(), str(spec_hint).lower(), str(tags.get("healthcare", "")).lower()]
        )
        specialization_match = 1 if (keyword and keyword in text_blob) else 0
        seen.add(key)
        el_lat = el.get("lat")
        el_lon = el.get("lon")
        distance_km = _distance_km(lat_c, lon_c, el_lat, el_lon)
        doctors.append(
            (
                specialization_match,
                distance_km,
                {
                    "name": name,
                    "specialization": str(spec_hint).strip()[:80],
                    "city": str(city).strip()[:80],
                    "phone": (tags.get("phone") or tags.get("contact:phone") or "N/A").strip(),
                    "email": (tags.get("email") or tags.get("contact:email") or "N/A").strip(),
                    "latitude": el_lat,
                    "longitude": el_lon,
                    "distance_km": round(distance_km, 2),
                    "map_search_url": _osm_map_link(el_lat, el_lon, name, city),
                    "source": "OpenStreetMap",
                },
            )
        )

    doctors.sort(key=lambda row: (-row[0], row[1]))
    return [row[2] for row in doctors[:limit]]


def _discover_here(*, location: str, specialization: str, limit: int) -> list[dict]:
    api_key = (getattr(settings, "HERE_API_KEY", "") or "").strip()
    if not api_key:
        return []

    query = f"{specialization} doctor in {location}".strip()
    params = {
        "apiKey": api_key,
        "q": query,
        "in": "countryCode:IND",
        "limit": max(1, min(limit, 10)),
    }
    url = "https://discover.search.hereapi.com/v1/discover?" + urlparse.urlencode(params)
    payload = _fetch_json(url)
    items = payload.get("items") or []
    doctors: list[dict] = []
    for item in items:
        position = item.get("position") or {}
        address = item.get("address") or {}
        doctors.append(
            {
                "name": (item.get("title") or "Nearby Doctor").strip(),
                "specialization": specialization,
                "city": (address.get("city") or address.get("county") or location).strip(),
                "phone": _first_phone(item) or "N/A",
                "email": "N/A",
                "latitude": position.get("lat"),
                "longitude": position.get("lng"),
                "map_search_url": item.get("href")
                or _map_search_link(item.get("title", ""), address.get("label", location)),
                "source": "HERE Places",
            }
        )
    return doctors[:limit]


def _discover_tomtom(*, location: str, specialization: str, limit: int) -> list[dict]:
    api_key = (getattr(settings, "TOMTOM_API_KEY", "") or "").strip()
    if not api_key:
        return []

    query = urlparse.quote(f"{specialization} doctor {location}".strip())
    params = {
        "key": api_key,
        "countrySet": "IN",
        "limit": max(1, min(limit, 10)),
    }
    url = (
        f"https://api.tomtom.com/search/2/poiSearch/{query}.json?"
        + urlparse.urlencode(params)
    )
    payload = _fetch_json(url)
    results = payload.get("results") or []
    doctors: list[dict] = []
    for row in results:
        address = row.get("address") or {}
        pos = row.get("position") or {}
        doctors.append(
            {
                "name": ((row.get("poi") or {}).get("name") or "Nearby Doctor").strip(),
                "specialization": specialization,
                "city": (address.get("municipality") or location).strip(),
                "phone": "N/A",
                "email": "N/A",
                "latitude": pos.get("lat"),
                "longitude": pos.get("lon"),
                "map_search_url": _map_search_link(
                    (row.get("poi") or {}).get("name", ""),
                    address.get("freeformAddress", location),
                ),
                "source": "TomTom Places",
            }
        )
    return doctors[:limit]


def _fetch_json(url: str) -> dict:
    req = urlrequest.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": _user_agent(),
        },
        method="GET",
    )
    try:
        with urlrequest.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urlerror.HTTPError:
        return {}
    except Exception:
        return {}


def _map_search_link(name: str, location: str) -> str:
    query = urlparse.quote_plus(f"{name} {location}".strip())
    return f"https://www.google.com/maps/search/?api=1&query={query}"


def _osm_map_link(lat: float | None, lon: float | None, name: str, city: str) -> str:
    if lat is None or lon is None:
        query = urlparse.quote_plus(f"{name} {city}".strip())
        return f"https://www.openstreetmap.org/search?query={query}"
    return f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=16/{lat}/{lon}"


def _nominatim_geocode(location: str) -> tuple[float, float] | None:
    if not location:
        return None
    params = {
        "q": f"{location}, India",
        "format": "jsonv2",
        "limit": 1,
    }
    url = "https://nominatim.openstreetmap.org/search?" + urlparse.urlencode(params)
    payload = _fetch_json(url)
    if not isinstance(payload, list) or not payload:
        return None
    try:
        return float(payload[0]["lat"]), float(payload[0]["lon"])
    except Exception:
        return None


def _fetch_overpass(query: str) -> dict:
    endpoint = "https://overpass-api.de/api/interpreter"
    data = urlparse.urlencode({"data": query}).encode("utf-8")
    req = urlrequest.Request(
        endpoint,
        data=data,
        headers={
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Accept": "application/json",
            "User-Agent": _user_agent(),
        },
        method="POST",
    )
    try:
        with urlrequest.urlopen(req, timeout=25) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return {}


def _user_agent() -> str:
    ua = (getattr(settings, "OSM_USER_AGENT", "") or "").strip()
    if ua:
        return ua
    return "HealthSync/1.0 (local-dev)"


def _first_phone(item: dict) -> str | None:
    contacts = item.get("contacts") or []
    for contact in contacts:
        phones = contact.get("phone") or []
        for phone in phones:
            value = (phone.get("value") or "").strip()
            if value:
                return value
    return None


def _distance_km(lat1: float, lon1: float, lat2: float | None, lon2: float | None) -> float:
    if lat2 is None or lon2 is None:
        return 9999.0
    # Lightweight equirectangular approximation is enough for ranking nearby POIs.
    from math import cos, radians, sqrt

    x = radians(lon2 - lon1) * cos(radians((lat1 + lat2) / 2.0))
    y = radians(lat2 - lat1)
    return 6371.0 * sqrt(x * x + y * y)
