"""Météo de la journée via Open-Meteo (gratuit, sans clé)."""
import json
from dataclasses import dataclass
from datetime import date, datetime

from . import config as C
from .tbm import get

CONDITIONS = {
    0: "Grand soleil", 1: "Plutôt dégagé", 2: "Éclaircies", 3: "Couvert",
    45: "Brouillard", 48: "Brouillard givrant",
    51: "Bruine", 53: "Bruine", 55: "Grosse bruine", 56: "Bruine verglaçante", 57: "Bruine verglaçante",
    61: "Pluie faible", 63: "Pluie", 65: "Forte pluie", 66: "Pluie verglaçante", 67: "Pluie verglaçante",
    71: "Neige faible", 73: "Neige", 75: "Forte neige", 77: "Grésil",
    80: "Averses", 81: "Averses", 82: "Grosses averses", 85: "Averses de neige", 86: "Averses de neige",
    95: "Orages", 96: "Orages et grêle", 99: "Orages et grêle",
}


@dataclass
class Weather:
    code: int
    t_max: float
    t_min: float
    sunrise: str
    sunset: str
    hourly: dict          # heure -> {temp, prob, mm, gust, dir}

    @property
    def condition(self):
        return CONDITIONS.get(self.code, "")

    def at(self, hour):
        return self.hourly.get(hour, {})


def forecast(d: date) -> Weather | None:
    url = ("https://api.open-meteo.com/v1/forecast"
           f"?latitude={C.LAT}&longitude={C.LON}&timezone=Europe/Paris"
           f"&start_date={d}&end_date={d}&timeformat=unixtime"
           "&hourly=temperature_2m,precipitation_probability,precipitation,"
           "wind_gusts_10m,wind_direction_10m"
           "&daily=weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset")
    try:
        data = json.loads(get(url, timeout=30))
    except Exception as exc:
        print("météo indisponible:", exc)
        return None
    h, dl = data["hourly"], data["daily"]
    # horodatages Unix convertis ici : l'API garde le décalage horaire du jour de la requête
    local = lambda ts: datetime.fromtimestamp(ts, C.TZ)
    hourly = {
        local(t).hour: dict(temp=h["temperature_2m"][i], prob=h["precipitation_probability"][i] or 0,
                            mm=h["precipitation"][i] or 0, gust=h["wind_gusts_10m"][i] or 0,
                            dir=h["wind_direction_10m"][i] or 0)
        for i, t in enumerate(h["time"])
    }
    return Weather(code=dl["weather_code"][0], t_max=dl["temperature_2m_max"][0],
                   t_min=dl["temperature_2m_min"][0], sunrise=f"{local(dl['sunrise'][0]):%H:%M}",
                   sunset=f"{local(dl['sunset'][0]):%H:%M}", hourly=hourly)
