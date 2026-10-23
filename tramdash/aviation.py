"""METAR de Mérignac et avions au-dessus de la maison (ADS-B via adsb.lol)."""
import json
import math
import os
from dataclasses import dataclass

from . import config as C
from .tbm import get

TYPES = {
    "A319": "A319", "A320": "A320", "A20N": "A320neo", "A321": "A321", "A21N": "A321neo",
    "A332": "A330", "A333": "A330", "A359": "A350", "BCS1": "A220", "BCS3": "A220",
    "B737": "737", "B738": "737-800", "B38M": "737 MAX", "B39M": "737 MAX", "B77W": "777",
    "B789": "787", "AT75": "ATR 72", "AT76": "ATR 72", "AT45": "ATR 42", "E190": "E190",
    "E195": "E195", "E75L": "E175", "CRJ9": "CRJ-900", "DH8D": "Dash 8", "C56X": "Citation",
    "PC12": "PC-12", "TBM9": "TBM 900", "TBM7": "TBM 700", "EC35": "hélico EC135",
    "EC45": "hélico H145", "A400": "A400M", "C172": "Cessna 172", "DR40": "Robin DR400",
}


def metar():
    try:
        raw = get(f"https://aviationweather.gov/api/data/metar?ids={C.METAR_STATION}&format=raw",
                  timeout=20).decode().strip().splitlines()
        return raw[0] if raw else None
    except Exception as exc:
        print("METAR indisponible:", exc)
        return None


@dataclass
class Plane:
    callsign: str
    type: str
    alt_ft: int
    dist_km: float
    bearing: float        # depuis la maison, degrés
    track: float
    airline: str = ""
    route: str = ""       # codes IATA, ex. BRU – BOD
    cities: str = ""      # ex. Brussels – Bordeaux/Mérignac


def _distance(lat1, lon1, lat2, lon2):
    dy = (lat2 - lat1) * 111.32
    dx = (lon2 - lon1) * 111.32 * math.cos(math.radians(lat1))
    return math.hypot(dx, dy), (math.degrees(math.atan2(dx, dy)) + 360) % 360


def _route(callsign):
    """Compagnie et origine -> destination, avec un cache sur disque."""
    path = os.path.join(C.CACHE_DIR, "routes.json")
    try:
        with open(path) as f:
            cache = json.load(f)
    except (OSError, ValueError):
        cache = {}
    if callsign not in cache:
        try:
            fr = json.loads(get(f"https://api.adsbdb.com/v0/callsign/{callsign}", timeout=10)
                            )["response"]["flightroute"]
            cache[callsign] = [fr["airline"]["name"] if fr.get("airline") else "",
                               f"{fr['origin']['iata_code']} – {fr['destination']['iata_code']}",
                               fr["origin"]["municipality"], fr["destination"]["municipality"]]
        except Exception:
            cache[callsign] = ["", "", "", ""]
        os.makedirs(C.CACHE_DIR, exist_ok=True)
        with open(path, "w") as f:
            json.dump(cache, f)
    return cache[callsign]


def positions():
    """Avions en vol dans le rayon : liste de dicts bruts (pour la page télé animée)."""
    nm = math.ceil(C.PLANES_RADIUS_KM / 1.852) + 1
    try:
        ac = json.loads(get(f"https://api.adsb.lol/v2/point/{C.HOME_LAT}/{C.HOME_LON}/{nm}",
                            timeout=20))["ac"]
    except Exception as exc:
        print("ADS-B indisponible:", exc)
        return None
    out = []
    for a in ac:
        if "lat" not in a or a.get("alt_baro") in (None, "ground"):
            continue
        if a["alt_baro"] < 100 and (a.get("gs") or 0) < 60:  # au sol (roulage)
            continue
        dist, brg = _distance(C.HOME_LAT, C.HOME_LON, a["lat"], a["lon"])
        if dist > C.PLANES_RADIUS_KM:
            continue
        out.append({"hex": a["hex"], "callsign": (a.get("flight") or a.get("r") or a["hex"]).strip(),
                    "type": TYPES.get(a.get("t", ""), a.get("t", "?")), "alt_ft": int(a["alt_baro"]),
                    "gs_kt": a.get("gs", 0) or 0, "track": a.get("track", 0) or 0,
                    "lat": a["lat"], "lon": a["lon"], "dist_km": round(dist, 2), "bearing": brg,
                    "vrate": a.get("baro_rate", 0) or 0, "reg": a.get("r", ""),
                    "squawk": a.get("squawk", ""), "icao_type": a.get("t", "")})
    return sorted(out, key=lambda p: p["dist_km"])


def planes(raw=None):
    raw = positions() if raw is None else raw
    if raw is None:
        return None
    out = [Plane(r["callsign"], r["type"], r["alt_ft"], r["dist_km"], r["bearing"], r["track"])
           for r in raw]
    for p in out[:4]:
        p.airline, p.route, origin, dest = _route(p.callsign)
        if origin:
            p.cities = f"{origin} – {dest}"
    return out
