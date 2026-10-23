"""Actus que le navigateur de la télé ne peut pas lire lui-même (pas de CORS) :
on les récupère ici et elles partent dans status.json."""
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

from .tbm import get

FEEDS = [
    ("AVIATION", "https://www.air-journal.fr/feed"),
]


def headlines(per_feed=8):
    out = []
    for cat, url in FEEDS:
        try:
            root = ET.fromstring(get(url, timeout=15))
        except Exception as exc:
            print("actu indisponible:", url, exc)
            continue
        for item in root.iter("item"):
            title = re.sub(r"\s+", " ", item.findtext("title") or "").strip()
            try:
                date = parsedate_to_datetime(item.findtext("pubDate")).isoformat()
            except (TypeError, ValueError):
                continue
            if title:
                out.append({"cat": cat, "title": title, "date": date})
            if len(out) >= per_feed:
                break
    return out
