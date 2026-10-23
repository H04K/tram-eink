"""python -m tramdash  ->  public/dashboard.png + dashboard.bin + status.json"""
import json
import os
import shutil
from datetime import datetime, timedelta

from . import aviation, news, render, tbm, weather
from . import config as C
from .render import fr


def at(day, hhmm):
    return datetime.combine(day, datetime.strptime(hhmm, "%H:%M").time(), C.TZ)


def commute(day, now, wx, deps):
    """Contenu du panneau ALLER."""
    walk = timedelta(minutes=C.WALK_MIN)
    live = day == now.date()
    lo, hi = at(day, C.TRAM_FROM), at(day, C.TRAM_UNTIL)
    window = [x for x in deps if lo <= x.dep <= hi + timedelta(seconds=59)]
    options = [x for x in window if x.dep - walk >= now] if live else window
    ideal = at(day, C.LEAVE_AT)
    best = next((x for x in options if x.dep - walk >= ideal), options[0] if options else None)

    h = wx.at(6) if wx else {}
    if not h:
        foot = ""
    elif h["mm"] >= 0.2 or h["prob"] >= 50:
        foot = f"pluie, {fr(h['mm'])} mm/h"
    elif h["prob"] >= 25:
        foot = f"risque d'averse {h['prob']}%"
    else:
        foot = "sec"
    if h:
        foot += f" · {round(h['temp'])}° au départ"
        if h["gust"] >= 45:
            foot += f" · rafales {round(h['gust'])} km/h"

    if best is None:
        later = [x for x in deps if x.dep > hi]
        return dict(big="RATÉ", urgent=live, foot=foot,
                    line1=f"plus de tram avant {C.TRAM_UNTIL}",
                    line2=f"prochain : {later[0].dep:%H:%M}" if later else "")
    leave = best.dep - walk
    mins = (leave - now).total_seconds() / 60

    def label(x):
        s = f"{x.dep:%H:%M}"
        return s + (f" ({x.delay_min:+d})" if x.realtime and x.delay_min else "")

    i = options.index(best)
    shown = options[i:i + 3]
    line2 = f"depuis {C.FROM_NAME}"
    if live and 0 <= mins < 60:
        line2 = f"dans {int(mins)} min · {C.FROM_NAME}"
    return dict(big=f"{leave:%H:%M}", urgent=live and mins <= 3, foot=foot,
                line1="tram " + " · ".join(label(x) for x in shown), line2=line2)


def refresh_s(mode, day, now):
    """Dans combien de secondes l'écran doit revenir chercher une image."""
    fast = 60 if C.LIVE else 300
    if mode == "commute" and day == now.date() and now < at(day, C.TRAM_UNTIL):
        return fast
    if mode == "planes" and 7 <= now.hour < 22:
        return fast if C.LIVE else 600
    return 1800


def build(now):
    """Calcule l'écran pour l'instant `now` : (image, statut)."""
    today, tomorrow = now.date(), now.date() + timedelta(days=1)
    if today.weekday() in C.WORKDAYS and now.hour < C.SWITCH_HOUR:
        mode, day = "commute", today
    elif now.hour >= C.SWITCH_HOUR and tomorrow.weekday() in C.WORKDAYS:
        mode, day = "commute", tomorrow
    else:
        mode, day = "planes", today

    state = dict(now=now, day=day, mode=mode, weather=weather.forecast(day),
                 metar=aviation.metar(), alerts=[])
    trams, positions = [], aviation.positions()  # la télé affiche les avions à toute heure
    if mode == "commute":
        deps = tbm.departures(day)
        state["commute"] = commute(day, now, state["weather"], deps)
        state["session"] = C.SESSIONS.get(day.weekday(), "REPOS")
        state["next_session"] = C.SESSIONS.get((day + timedelta(days=1)).weekday())
        state["alerts"] = tbm.alerts(now)
        lo = at(day, C.TRAM_FROM) - timedelta(hours=1)
        hi = at(day, C.TRAM_UNTIL) + timedelta(hours=1)
        trams = [{"trip_id": x.trip_id, "dep": x.dep.isoformat(), "arr": x.arr.isoformat(),
                  "delay_min": x.delay_min, "realtime": x.realtime}
                 for x in deps if lo <= x.dep <= hi]
    else:
        state["planes"] = aviation.planes(positions)

    status = {"generated": now.isoformat(), "mode": mode, "day": day.isoformat(),
              "refresh_s": refresh_s(mode, day, now), "commute": state.get("commute"),
              "metar": state["metar"], "alerts": state["alerts"],
              # pour la page télé animée, qui recalcule tout chaque seconde
              "trams": trams, "planes": positions, "news": news.headlines(), "config": tv_config()}
    return render.render(state), status


def tv_config():
    return {"route_id": C.ROUTE_ID, "route": C.ROUTE_NAME, "from_stop": C.FROM_STOP,
            "to_stop": C.TO_STOP, "from_name": C.FROM_NAME, "to_name": C.TO_NAME,
            "walk_min": C.WALK_MIN, "leave_at": C.LEAVE_AT, "tram_from": C.TRAM_FROM,
            "tram_until": C.TRAM_UNTIL, "workdays": sorted(C.WORKDAYS),
            "switch_hour": C.SWITCH_HOUR, "sessions": C.SESSIONS, "muscles": C.MUSCLES,
            "home": [C.HOME_LAT, C.HOME_LON], "weather": [C.LAT, C.LON],
            "radius_km": C.PLANES_RADIUS_KM, "rt_url": C.GTFS_RT_TRIPS_URL}


def main():
    now = datetime.now(C.TZ)
    if os.getenv("NOW"):  # pour tester : NOW="2026-10-26T06:10"
        now = datetime.fromisoformat(os.environ["NOW"]).replace(tzinfo=C.TZ)
    img, status = build(now)

    os.makedirs(C.OUT_DIR, exist_ok=True)
    img.save(os.path.join(C.OUT_DIR, "dashboard.png"))
    with open(os.path.join(C.OUT_DIR, "dashboard.bin"), "wb") as f:
        f.write(render.to_bin(img))
    with open(os.path.join(C.OUT_DIR, "status.json"), "w") as f:
        json.dump(status, f, ensure_ascii=False, indent=1)
    # pages pour un navigateur (télé, tablette) : la version animée et l'image e-ink seule
    here = os.path.dirname(__file__)
    shutil.copy(os.path.join(here, "tv.html"), os.path.join(C.OUT_DIR, "index.html"))
    shutil.copy(os.path.join(here, "image.html"), os.path.join(C.OUT_DIR, "image.html"))
    print("ok:", status["mode"], status["generated"], status.get("commute") or "")


if __name__ == "__main__":
    main()
