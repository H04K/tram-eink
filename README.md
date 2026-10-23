# tram-eink

Écran e-ink à côté de la porte (reTerminal E1001, 800×480 noir et blanc), inspiré de
[Cycle or train?](https://whitebeard.blog/posts/cycle-or-train/).

- **En semaine** : l'heure à laquelle partir du 33 rue de Pessac pour attraper le tram F
  à Palais de Justice entre 06:40 et 07:00 (11 min à pied), avec retards en temps réel.
  À côté, la séance de sport du jour (push / pull / legs / push / pull). Après midi,
  l'écran prépare le lendemain.
- **Le week-end** : les avions au-dessus de la maison (radar 20 km, compagnie, route, altitude).
- **Partout** : météo du jour, pluie heure par heure, METAR de Mérignac (LFBD),
  perturbations TBM sur la ligne F.

Le matériel ne fait que télécharger une image : tout est calculé par GitHub Actions et
publié sur GitHub Pages.

## Sorties (`public/`)

| fichier | contenu |
|---|---|
| `dashboard.png` | l'image 800×480 |
| `dashboard.bin` | la même en brut : 1 bit/pixel, MSB = pixel de gauche, 1 = noir (48 000 octets) |
| `status.json` | mode, heure de départ, METAR, et `refresh_s` : dans combien de secondes revenir |

## Sources (gratuites, sans clé)

- Horaires TBM : GTFS + GTFS-RT de Bordeaux Métropole (open data)
- Météo : [Open-Meteo](https://open-meteo.com)
- METAR : [aviationweather.gov](https://aviationweather.gov)
- Avions : [adsb.lol](https://adsb.lol) (ADS-B), routes via [adsbdb](https://www.adsbdb.com)
- Police : [Fraunces](https://fonts.google.com/specimen/Fraunces) (OFL, `fonts/OFL.txt`)

## Lancer en local

```sh
pip install -r requirements.txt
python -m tramdash                                   # maintenant
NOW=2026-10-26T06:12 python -m tramdash              # simuler une heure
COLOR=1 python -m tramdash                           # version E1002 (6 couleurs)
```

Tous les réglages (arrêts, horaires, séances, rayon radar…) sont dans
`tramdash/config.py` et se surchargent par variable d'environnement.

## Mise en ligne

1. Pousser ce dépôt sur GitHub.
2. *Settings → Pages → Source : GitHub Actions*.
3. *Actions → render → Run workflow* pour un premier rendu.
4. L'image est alors sur `https://<compte>.github.io/tram-eink/dashboard.png`.
