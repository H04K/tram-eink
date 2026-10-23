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
from . import render
from .__main__ import build

_lock = threading.Lock()
_last = {"at": 0.0, "img": None, "status": None}


def current():
    """Une image par tranche de 30 s : status.json et dashboard.bin parlent de la même."""
    with _lock:
        if time.time() - _last["at"] > 30:
            _last["img"], _last["status"] = build(datetime.now(C.TZ))
            _last["at"] = time.time()
        return _last["img"], _last["status"]


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0]
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
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    print(f"tramdash en direct sur http://0.0.0.0:{port}/dashboard.png")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
