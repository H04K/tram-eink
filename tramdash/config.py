"""Réglages. Tout se surcharge par variable d'environnement."""
import os
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Paris")

# Maison : 33 rue de Pessac, Bordeaux
HOME_LAT = float(os.getenv("HOME_LAT", "44.830498"))
HOME_LON = float(os.getenv("HOME_LON", "-0.579899"))

# Tram (identifiants du GTFS TBM)
ROUTE_ID = os.getenv("ROUTE_ID", "164")          # Tram F
ROUTE_NAME = os.getenv("ROUTE_NAME", "F")
FROM_STOP = os.getenv("FROM_STOP", "3720")       # Palais de Justice, quai direction Aéroport
TO_STOP = os.getenv("TO_STOP", "9090")           # Mérignac Soleil
FROM_NAME = os.getenv("FROM_NAME", "Palais de Justice")
TO_NAME = os.getenv("TO_NAME", "Mérignac Soleil")

WALK_MIN = int(os.getenv("WALK_MIN", "11"))      # maison -> Palais de Justice (814 m)
LEAVE_AT = os.getenv("LEAVE_AT", "06:29")        # départ idéal de la maison
TRAM_FROM = os.getenv("TRAM_FROM", "06:40")      # fenêtre de trams acceptable
TRAM_UNTIL = os.getenv("TRAM_UNTIL", "07:00")
WORKDAYS = {int(d) for d in os.getenv("WORKDAYS", "0,1,2,3,4").split(",")}  # 0 = lundi
SWITCH_HOUR = int(os.getenv("SWITCH_HOUR", "12"))  # après midi : on prépare le lendemain

# Séances de sport, par jour (0 = lundi)
SESSIONS = {0: "PUSH", 1: "PULL", 2: "LEGS", 3: "PUSH", 4: "PULL"}
MUSCLES = {
    "PULL": "dos · biceps · arrière d'épaule",
    "PUSH": "pecs · épaules · triceps",
    "LEGS": "quadris · ischios · fessiers · mollets",
}

# Météo (Open-Meteo)
LAT = float(os.getenv("LAT", "44.835"))
LON = float(os.getenv("LON", "-0.62"))
CHART_HOURS = range(5, 19)                       # pluie heure par heure, 5h -> 18h
COMMUTE_HOURS = (6, 7)                           # heures soulignées sur le graphe

# Aviation
METAR_STATION = os.getenv("METAR_STATION", "LFBD")
PLANES_RADIUS_KM = float(os.getenv("PLANES_RADIUS_KM", "20"))
# relais Cloudflare (worker/planes.js) pour que la télé lise les avions chaque seconde
ADSB_RELAY = os.getenv("ADSB_RELAY") or "https://tram-eink.diplodopote.workers.dev"

# Écran : reTerminal E1001, 7,5" noir et blanc (COLOR=1 pour le E1002 Spectra 6)
COLOR = os.getenv("COLOR", "0") == "1"
WIDTH = int(os.getenv("WIDTH", "800"))
HEIGHT = int(os.getenv("HEIGHT", "480"))

# Flux TBM open data (clé publique fournie par Bordeaux Métropole)
_KEY = "opendata-bordeaux-metropole-flux-gtfs-rt"
GTFS_STATIC_URL = f"https://bdx.mecatran.com/utw/ws/gtfsfeed/static/bordeaux?apiKey={_KEY}"
GTFS_RT_TRIPS_URL = f"https://bdx.mecatran.com/utw/ws/gtfsfeed/realtime/bordeaux?apiKey={_KEY}"
GTFS_RT_ALERTS_URL = f"https://bdx.mecatran.com/utw/ws/gtfsfeed/alerts/bordeaux?apiKey={_KEY}"

# LIVE=1 : l'image est calculée à chaque demande de l'écran (python -m tramdash.server),
# qui revient alors toutes les minutes au lieu de toutes les 5-10 min.
LIVE = os.getenv("LIVE", "0") == "1"

CACHE_DIR = os.getenv("CACHE_DIR", ".cache")
OUT_DIR = os.getenv("OUT_DIR", "public")
