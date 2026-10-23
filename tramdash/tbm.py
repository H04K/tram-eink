"""Horaires TBM : théoriques (GTFS) + temps réel (GTFS-RT) + perturbations."""
import csv
import io
import json
import os
import time
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from google.transit import gtfs_realtime_pb2

from . import config as C


@dataclass
class Departure:
    trip_id: str
    dep: datetime          # départ de FROM_STOP (temps réel si dispo)
    arr: datetime          # arrivée à TO_STOP
    delay_min: int = 0
    realtime: bool = False


def get(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "tram-eink"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 ** (attempt + 1))


# --- GTFS statique --------------------------------------------------------

def _load_static():
    """Extrait seulement ce qui sert (FROM -> TO sur la ligne) et le met en cache du jour."""
    os.makedirs(C.CACHE_DIR, exist_ok=True)
    cache = os.path.join(C.CACHE_DIR, f"static-{C.ROUTE_ID}-{C.FROM_STOP}-{C.TO_STOP}.json")
    if os.path.exists(cache) and time.time() - os.path.getmtime(cache) < 20 * 3600:
        with open(cache) as f:
            return json.load(f)

    z = zipfile.ZipFile(io.BytesIO(get(C.GTFS_STATIC_URL, timeout=180)))

    def rows(name):
        return csv.DictReader(io.TextIOWrapper(z.open(name), encoding="utf-8-sig"))

    trips = {r["trip_id"]: r["service_id"] for r in rows("trips.txt") if r["route_id"] == C.ROUTE_ID}
    times = {}
    for r in rows("stop_times.txt"):
        if r["trip_id"] in trips and r["stop_id"] in (C.FROM_STOP, C.TO_STOP):
            times.setdefault(r["trip_id"], {})[r["stop_id"]] = (int(r["stop_sequence"]), r["departure_time"])
    legs = []
    for tid, s in times.items():
        if C.FROM_STOP in s and C.TO_STOP in s and s[C.FROM_STOP][0] < s[C.TO_STOP][0]:
            legs.append([tid, trips[tid], s[C.FROM_STOP][1], s[C.TO_STOP][1]])

    calendar = {r["service_id"]: r for r in rows("calendar.txt")}
    exceptions = {}
    for r in rows("calendar_dates.txt"):
        exceptions.setdefault(r["date"], {})[r["service_id"]] = r["exception_type"]

    data = {"legs": legs, "calendar": calendar, "exceptions": exceptions}
    with open(cache, "w") as f:
        json.dump(data, f)
    return data


def _active_services(data, d: date):
    key = d.strftime("%Y%m%d")
    day = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][d.weekday()]
    active = {sid for sid, c in data["calendar"].items()
              if c[day] == "1" and c["start_date"] <= key <= c["end_date"]}
    for sid, kind in data["exceptions"].get(key, {}).items():
        if kind == "1":
            active.add(sid)
        else:
            active.discard(sid)
    return active


def _at(d: date, hms: str) -> datetime:
    h, m, s = map(int, hms.split(":"))
    return datetime.combine(d, datetime.min.time(), C.TZ) + timedelta(hours=h, minutes=m, seconds=s)


def scheduled(d: date):
    data = _load_static()
    active = _active_services(data, d)
    out = [Departure(tid, _at(d, dep), _at(d, arr))
           for tid, sid, dep, arr in data["legs"] if sid in active]
    return sorted(out, key=lambda x: x.dep)


# --- Temps réel -----------------------------------------------------------

def realtime():
    """{trip_id: (départ, arrivée)} pour les courses qui passent par FROM puis TO."""
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(get(C.GTFS_RT_TRIPS_URL))
    out = {}
    for e in feed.entity:
        tu = e.trip_update
        if tu.trip.route_id != C.ROUTE_ID:
            continue
        stops = {s.stop_id: s for s in tu.stop_time_update}
        a, b = stops.get(C.FROM_STOP), stops.get(C.TO_STOP)
        if not a or not b or a.stop_sequence >= b.stop_sequence:
            continue
        dep = a.departure.time or a.arrival.time
        arr = b.arrival.time or b.departure.time
        if dep and arr:
            out[tu.trip.trip_id] = (datetime.fromtimestamp(dep, C.TZ), datetime.fromtimestamp(arr, C.TZ))
    return out


def departures(d: date):
    """Horaires du jour, corrigés par le temps réel quand il existe."""
    sched = scheduled(d)
    try:
        rt = realtime() if d == datetime.now(C.TZ).date() else {}
    except Exception as exc:
        print("temps réel indisponible:", exc)
        rt = {}
    known = set()
    for x in sched:
        if x.trip_id in rt:
            dep, arr = rt[x.trip_id]
            if abs((dep - x.dep).total_seconds()) > 3600:  # id réutilisé : pas la même course
                continue
            x.delay_min = round((dep - x.dep).total_seconds() / 60)
            x.dep, x.arr, x.realtime = dep, arr, True
            known.add(x.trip_id)
    # courses ajoutées en temps réel (renforts, "nt_...")
    for tid, (dep, arr) in rt.items():
        if tid not in known and dep.date() == d:
            sched.append(Departure(tid, dep, arr, 0, True))
    # plusieurs calendriers peuvent couvrir le même jour : une course par horaire
    out = []
    for x in sorted(sched, key=lambda x: (x.dep, not x.realtime)):
        if out and abs((x.dep - out[-1].dep).total_seconds()) < 60:
            continue
        out.append(x)
    return out


def alerts(now: datetime):
    """Titres des perturbations en cours sur la ligne."""
    try:
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(get(C.GTFS_RT_ALERTS_URL))
    except Exception as exc:
        print("alertes indisponibles:", exc)
        return []
    ts = now.timestamp()
    out = []
    for e in feed.entity:
        a = e.alert
        if not any(i.route_id == C.ROUTE_ID for i in a.informed_entity):
            continue
        if a.active_period and not any((not p.start or p.start <= ts) and (not p.end or ts <= p.end)
                                       for p in a.active_period):
            continue
        if a.header_text.translation:
            out.append(a.header_text.translation[0].text)
    return out
