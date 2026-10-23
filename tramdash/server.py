"""Mode direct : python -m tramdash.server  (port 8080 par défaut)

L'écran demande /status.json puis /dashboard.bin : l'image est calculée à ce moment-là,
avec le tram et les avions de la minute. /dashboard.png sert à vérifier dans un navigateur.
"""
import io
import json
import os
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import config as C
from . import aviation, render
from .__main__ import build

_lock = threading.Lock()
_last = {"at": 0.0, "img": None, "status": None}
_planes = {"at": 0.0, "data": None}


def current():
    """Une image par tranche de 30 s : status.json et dashboard.bin parlent de la même."""
    with _lock:
        if time.time() - _last["at"] > 30:
            _last["img"], _last["status"] = build(datetime.now(C.TZ))
            _last["at"] = time.time()
        return _last["img"], _last["status"]


def live_planes():
    """Positions ADS-B fraîches (5 s max) : la page télé les anime en continu."""
    with _lock:
        if time.time() - _planes["at"] > 5:
            _planes["data"], _planes["at"] = aviation.positions(), time.time()
        return _planes["data"]


PAGES = {"/": "tv.html", "/index.html": "tv.html", "/image.html": "image.html"}


class Handler(BaseHTTPRequestHandler):
    def send(self, body, kind):
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in PAGES:
            with open(os.path.join(os.path.dirname(__file__), PAGES[path]), "rb") as f:
                self.send(f.read(), "text/html; charset=utf-8")
            return
        if path == "/planes.json":
            self.send(json.dumps({"live": True, "planes": live_planes()}).encode(), "application/json")
            return
        if path not in ("/status.json", "/dashboard.bin", "/dashboard.png"):
            self.send_error(404)
            return
        try:
            img, status = current()
        except Exception as exc:
            self.send_error(500, str(exc))
            return
        if path == "/status.json":
            body, kind = json.dumps(status, ensure_ascii=False).encode(), "application/json"
        elif path == "/dashboard.bin":
            body, kind = render.to_bin(img), "application/octet-stream"
        else:
            buf = io.BytesIO()
            img.save(buf, "PNG")
            body, kind = buf.getvalue(), "image/png"
        self.send(body, kind)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    print(f"tramdash en direct sur http://0.0.0.0:{port}/dashboard.png")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
