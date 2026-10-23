"""Dessine l'écran (800x480, noir et blanc ou E Ink Spectra 6) dans le style « cycle or train »."""
import math
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import config as C

# Les 6 encres de l'écran. On dessine directement avec ces couleurs : pas de tramage.
BLACK, WHITE, YELLOW, RED, BLUE, GREEN = 0, 1, 2, 3, 4, 5
PALETTE = [(0, 0, 0), (255, 255, 255), (255, 230, 0), (200, 0, 0), (0, 60, 200), (0, 150, 60)]
# Codes couleur 4 bits du contrôleur Spectra 6 (ordre GxEPD2 / Seeed)
PANEL_CODE = {BLACK: 0x0, WHITE: 0x1, YELLOW: 0x2, RED: 0x3, BLUE: 0x5, GREEN: 0x6}
if not C.COLOR:  # écran noir et blanc : toutes les encres deviennent du noir
    YELLOW = RED = BLUE = GREEN = BLACK

JOURS = ["LUNDI", "MARDI", "MERCREDI", "JEUDI", "VENDREDI", "SAMEDI", "DIMANCHE"]
MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]

# LFBD : pistes 05/23 (3100 m, 049°) et 11/29 (2415 m, 107°), centrées sur l'aéroport
LFBD = (44.8283, -0.7156)
RUNWAYS = [(49, 3.1), (107, 2.4)]


def serif(size, weight=700, italic=False):
    f = ImageFont.truetype(f"fonts/Fraunces{'-Italic' if italic else ''}.ttf", size)
    f.set_variation_by_axes([min(144, max(9, size)), weight, 0, 0])
    return f


def mono(size):
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", size)
    except OSError:
        return ImageFont.load_default(size)


def fit(d, text, weight, size, width):
    """Plus grande taille (<= size) pour que le texte tienne dans width."""
    while size > 12:
        f = serif(size, weight)
        if d.textlength(text, font=f) <= width:
            return f
        size -= 2
    return serif(size, weight)


def fr(x, digits=1):
    return f"{x:.{digits}f}".replace(".", ",")


def ft(alt):
    return f"{alt:,}".replace(",", " ") + " ft"


# --- pictos ---------------------------------------------------------------

def cloud(d, x, y, s, ink=BLACK):
    """Nuage au trait, (x, y) = coin haut gauche, s = largeur."""
    k = s / 100
    mask = Image.new("L", (s + 2, int(s * 0.8)), 0)
    m = ImageDraw.Draw(mask)
    for box in [(0, 30, 44, 76), (18, 6, 68, 56), (52, 22, 98, 76)]:
        m.ellipse([v * k for v in box], fill=255)
    m.rectangle([20 * k, 30 * k, 76 * k, 76 * k], fill=255)
    outline = Image.eval(mask.filter(ImageFilter.MinFilter(11)), lambda v: 255 - v)
    d.bitmap((x, y), Image.composite(mask, Image.new("L", mask.size, 0), outline), fill=ink)


def sun(d, cx, cy, r, ink=BLACK):
    for k in range(8):
        a = math.radians(k * 45 + 22.5)
        d.line([(cx + math.cos(a) * (r + 7), cy + math.sin(a) * (r + 7)),
                (cx + math.cos(a) * (r + 18), cy + math.sin(a) * (r + 18))], fill=ink, width=5)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=ink, width=6)


def weather_icon(d, x, y, code):
    if code <= 1:
        sun(d, x + 50, y + 48, 24)
        return
    if code == 2:
        sun(d, x + 30, y + 28, 16)
    cloud(d, x, y + 4, 100)
    if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
        for i in range(3):
            d.line([(x + 36 + i * 16, y + 88), (x + 28 + i * 16, y + 104)], fill=BLACK, width=6)
    elif code in (71, 73, 75, 77, 85, 86):
        for i in range(3):
            d.text((x + 32 + i * 18, y + 100), "*", font=serif(34, 900), fill=BLACK, anchor="mm")
    elif code >= 95:
        d.polygon([(x + 52, y + 80), (x + 40, y + 98), (x + 50, y + 98), (x + 44, y + 114),
                   (x + 62, y + 92), (x + 52, y + 92), (x + 60, y + 80)], fill=BLACK)


def tram_icon(d, x, y, ink=WHITE):
    d.line([(x + 24, y), (x + 24, y - 8)], fill=ink, width=4)
    d.rounded_rectangle([x, y, x + 48, y + 54], radius=12, outline=ink, width=5)
    d.rounded_rectangle([x + 9, y + 10, x + 39, y + 28], radius=3, outline=ink, width=4)
    d.ellipse([x + 10, y + 36, x + 18, y + 44], fill=ink)
    d.ellipse([x + 30, y + 36, x + 38, y + 44], fill=ink)
    d.line([(x + 12, y + 54), (x + 2, y + 68)], fill=ink, width=5)
    d.line([(x + 36, y + 54), (x + 46, y + 68)], fill=ink, width=5)


def dumbbell_icon(d, x, y, ink=WHITE):
    d.line([(x + 4, y + 30), (x + 56, y + 30)], fill=ink, width=6)
    for px, h in ((x + 8, 44), (x + 18, 30), (x + 34, 30), (x + 44, 44)):
        d.rounded_rectangle([px, y + 30 - h // 2, px + 8, y + 30 + h // 2], radius=3, fill=ink)


def plane_glyph(d, cx, cy, track, size, ink):
    a = math.radians(track)
    pts = [(0, -1), (0.75, 0.8), (0, 0.4), (-0.75, 0.8)]
    d.polygon([(cx + (px * math.cos(a) - py * math.sin(a)) * size,
                cy + (px * math.sin(a) + py * math.cos(a)) * size) for px, py in pts], fill=ink)


# --- blocs ----------------------------------------------------------------

def header(d, state):
    W = C.WIDTH
    day, now = state["day"], state["now"]
    name = JOURS[day.weekday()]
    d.text((22, 48), name, font=fit(d, name, 900, 84, 560), fill=BLACK, anchor="lm")
    f = serif(22, 400)
    d.text((W - 22, 32), f"{day.day} {MOIS[day.month - 1]}", font=f, fill=BLACK, anchor="rm")
    d.text((W - 22, 60), f"màj {now:%H:%M}", font=f, fill=BLACK, anchor="rm")
    d.line([(22, 96), (W - 22, 96)], fill=BLACK, width=4)


def weather_row(d, wx, seed):
    if wx is None:
        d.text((24, 160), "Météo indisponible", font=serif(26, 600), fill=BLACK, anchor="lm")
        return
    weather_icon(d, 26, 104, wx.code)
    big = serif(64, 800)
    t = f"{round(wx.t_max)}°"
    d.text((150, 100), t, font=big, fill=BLACK)
    d.text((150 + d.textlength(t, font=big) + 8, 126), f"/ {round(wx.t_min)}°",
           font=serif(30, 400), fill=BLACK)
    d.text((152, 182), wx.condition, font=serif(26, 600), fill=BLACK, anchor="lm")
    d.text((152, 210), f"lever {wx.sunrise}  ·  coucher {wx.sunset}", font=serif(16, 500),
           fill=BLACK, anchor="lm")

    # pluie heure par heure : densité de gouttes = probabilité, pente = vent
    x0, x1, top, axis = 430, 778, 108, 182
    hours = list(C.CHART_HOURS)
    step = (x1 - x0) / len(hours)
    rng = random.Random(seed)
    for i, h in enumerate(hours):
        hw = wx.at(h)
        cx = x0 + step * (i + 0.5)
        slant = math.sin(math.radians(hw.get("dir", 270) - 180)) * 0.5
        for _ in range(round(hw.get("prob", 0) / 9)):
            px, py = rng.uniform(cx - step / 2 + 3, cx + step / 2 - 6), rng.uniform(top, axis - 13)
            d.line([(px, py), (px + slant * 9, py + 9)], fill=BLUE, width=3)
        if h in C.COMMUTE_HOURS:
            d.rectangle([cx - step / 2 + 1, axis + 1, cx + step / 2 - 1, axis + 7], fill=BLACK)
        d.text((cx, axis + 18), str(h), font=serif(15, 500), fill=BLACK, anchor="mm")
    d.line([(x0, axis), (x1, axis)], fill=BLACK, width=2)
    d.text((x1, 214), "risque de pluie par heure", font=serif(15, 400), fill=BLACK, anchor="rm")


def panel(d, box, label, fill=BLACK, ink=WHITE):
    d.rectangle(box, fill=fill, outline=BLACK, width=4)
    d.text((box[0] + 18, box[1] + 22), label, font=serif(17, 800), fill=ink, anchor="lm")


def commute_panel(d, box, state):
    c = state["commute"]
    x0, y0, x1, y1 = box
    # urgent : panneau rouge en couleur, panneau inversé (blanc) en noir et blanc
    fill, ink = (RED, WHITE) if c["urgent"] and C.COLOR else \
        (WHITE, BLACK) if c["urgent"] else (BLACK, WHITE)
    panel(d, box, "FILE ! PARS À" if c["urgent"] else "ALLER · PARS À", fill, ink)
    tram_icon(d, x0 + 22, y0 + 60, ink)
    tx = x0 + 92
    d.text((tx, y0 + 34), c["big"], font=fit(d, c["big"], 900, 80, x1 - tx - 12), fill=ink)
    small = serif(19, 600)
    d.text((tx, y0 + 130), c["line1"], font=fit(d, c["line1"], 600, 19, x1 - tx - 12), fill=ink)
    d.text((tx, y0 + 155), c["line2"], font=fit(d, c["line2"], 600, 19, x1 - tx - 12), fill=ink)
    d.text((x0 + 18, y1 - 22), c["foot"], font=serif(19, 500), fill=ink, anchor="lm")


def session_panel(d, box, state):
    x0, y0, x1, y1 = box
    s = state["session"]
    panel(d, box, "SÉANCE")
    dumbbell_icon(d, x0 + 18, y0 + 66)
    tx = x0 + 92
    d.text((tx, y0 + 34), s, font=fit(d, s, 900, 80, x1 - tx - 12), fill=WHITE)
    muscles = C.MUSCLES.get(s, "")
    d.text((tx, y0 + 130), muscles, font=fit(d, muscles, 600, 19, x1 - tx - 12), fill=WHITE)
    nxt = state["next_session"]
    d.text((x0 + 18, y1 - 22), f"demain : {nxt.lower() if nxt else 'repos'}",
           font=serif(19, 500), fill=WHITE, anchor="lm")


def radar(d, box, planes):
    x0, y0, x1, y1 = box
    d.rectangle(box, outline=BLACK, width=3)
    d.text((x0 + 16, y0 + 20), f"RADAR · {round(C.PLANES_RADIUS_KM)} KM", font=serif(15, 800),
           fill=BLACK, anchor="lm")
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2 + 4
    r = (y1 - y0) / 2 - 10
    km = r / C.PLANES_RADIUS_KM

    def xy(lat, lon):
        dy = (lat - C.HOME_LAT) * 111.32
        dx = (lon - C.HOME_LON) * 111.32 * math.cos(math.radians(C.HOME_LAT))
        return cx + dx * km, cy - dy * km

    R = C.PLANES_RADIUS_KM
    for ring in (round(R / 6), round(R / 2), round(R)):
        rr = ring * km
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=BLACK, width=1)
        d.text((cx + 3, cy - rr + 2), f"{ring} km", font=serif(11, 500), fill=BLACK)
    ax, ay = xy(*LFBD)
    for hdg, length in RUNWAYS:
        a = math.radians(hdg)
        dx, dy = math.sin(a) * length / 2 * km, -math.cos(a) * length / 2 * km
        d.line([(ax - dx, ay - dy), (ax + dx, ay + dy)], fill=BLACK, width=5)
    d.text((ax, ay + 18), "LFBD", font=serif(13, 700), fill=BLACK, anchor="mm")
    d.polygon([(cx, cy - 10), (cx + 8, cy - 3), (cx - 8, cy - 3)], fill=RED)
    d.rectangle([cx - 6, cy - 3, cx + 6, cy + 6], fill=RED)
    for p in planes or []:
        a = math.radians(p.bearing)
        px, py = cx + math.sin(a) * p.dist_km * km, cy - math.cos(a) * p.dist_km * km
        plane_glyph(d, px, py, p.track, 11, BLUE if p.alt_ft < 5000 else BLACK)
        d.text((px + 12, py - 2), p.callsign, font=serif(12, 700), fill=BLACK, anchor="lm")


def planes_panel(d, box, planes):
    x0, y0, x1, y1 = box
    panel(d, box, "AU-DESSUS DE CHEZ TOI")
    tx, w = x0 + 18, x1 - x0 - 36
    if planes is None:
        d.text((tx, y0 + 60), "PAS DE DONNÉES", font=serif(40, 900), fill=WHITE)
        return
    if not planes:
        d.text((tx, y0 + 46), "CIEL VIDE", font=serif(64, 900), fill=WHITE)
        d.text((tx, y0 + 130), f"aucun avion à moins de {round(C.PLANES_RADIUS_KM)} km",
               font=serif(19, 600), fill=WHITE)
        return
    p = planes[0]
    d.text((tx, y0 + 36), p.callsign, font=fit(d, p.callsign, 900, 54, w), fill=WHITE)
    who = " · ".join(x for x in (p.airline, p.type) if x)
    d.text((tx, y0 + 102), who, font=fit(d, who, 600, 19, w), fill=WHITE)
    where = p.cities or p.route or "route inconnue"
    d.text((tx, y0 + 126), where, font=fit(d, where, 600, 19, w), fill=WHITE)
    d.text((tx, y0 + 150), f"{ft(p.alt_ft)} · à {fr(p.dist_km)} km", font=serif(19, 600), fill=WHITE)
    y = y0 + 180
    f = serif(15, 500)
    for q in planes[1:3]:
        d.text((tx, y), q.callsign, font=serif(15, 800), fill=WHITE)
        d.text((tx + 100, y), q.route or q.type, font=f, fill=WHITE)
        d.text((x1 - 18, y), f"{ft(q.alt_ft)} · {fr(q.dist_km)} km", font=f, fill=WHITE, anchor="ra")
        y += 18


def footer(d, state):
    W, H = C.WIDTH, C.HEIGHT
    if state.get("alerts"):
        d.rectangle([0, H - 28, W, H], fill=RED)
        msg, f = "⚠ " + state["alerts"][0], serif(16, 600)
        while d.textlength(msg, font=f) > W - 40:
            msg = msg[:-2] + "…"
        d.text((W // 2, H - 14), msg, font=f, fill=WHITE, anchor="mm")
    elif state.get("metar"):
        # METAR sans la prévision TEMPO/BECMG ni les "///" des stations automatiques
        msg = state["metar"].removeprefix("METAR ").split(" TEMPO")[0].split(" BECMG")[0]
        msg, f = msg.replace("///", ""), mono(14)
        while d.textlength(msg, font=f) > W - 40:
            msg = msg.rsplit(" ", 1)[0]
        d.text((W // 2, H - 15), msg, font=f, fill=BLACK, anchor="mm")


def render(state) -> Image.Image:
    W = C.WIDTH
    img = Image.new("P", (W, C.HEIGHT), WHITE)
    img.putpalette([v for c in PALETTE for v in c])
    d = ImageDraw.Draw(img)
    header(d, state)
    weather_row(d, state["weather"], state["day"].toordinal())
    left, right = (22, 234, 390, 446), (408, 234, W - 22, 446)
    if state["mode"] == "commute":
        commute_panel(d, left, state)
        session_panel(d, right, state)
    else:
        radar(d, left, state["planes"])
        planes_panel(d, right, state["planes"])
    footer(d, state)
    return img


def to_bin(img: Image.Image) -> bytes:
    """Noir et blanc : 1 bit par pixel, MSB = pixel de gauche, 1 = noir.
    Couleur : 4 bits par pixel (2 pixels par octet, pixel de gauche dans les bits forts),
    codes couleur natifs du Spectra 6 : l'ESP32 n'a qu'à pousser les octets."""
    if not C.COLOR:
        return bytes(b ^ 0xFF for b in img.convert("L").convert("1").tobytes())
    px = [PANEL_CODE[p] for p in img.getdata()]
    return bytes((px[i] << 4) | px[i + 1] for i in range(0, len(px), 2))
