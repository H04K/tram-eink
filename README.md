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

## Mode direct (recommandé si une machine tourne en permanence à la maison)

GitHub Pages ne sert que des images calculées d'avance (toutes les 5-10 min, cron
GitHub pas toujours ponctuel). En mode direct, l'image est calculée **au moment où
l'écran la demande**, et l'écran revient toutes les minutes pendant le trajet et le
week-end en journée :

```sh
LIVE=1 python -m tramdash.server      # http://<ip-de-la-machine>:8080/dashboard.png
```

N'importe quoi d'allumé en continu suffit : Raspberry Pi, NAS, vieux PC. Avec un
rafraîchissement par minute, l'écran tient quelques jours sur batterie : mieux vaut le
laisser branché en USB-C.

## Mettre l'image sur l'écran (firmware)

`firmware/tram_eink/tram_eink.ino`, pour Arduino IDE :

1. Gestionnaire de cartes : ajouter
   `https://espressif.github.io/arduino-esp32/package_esp32_index.json`, installer **esp32**.
2. Gestionnaire de bibliothèques : installer **GxEPD2**.
3. Copier `secrets.example.h` en `secrets.h`, mettre le Wi-Fi et `BASE_URL`
   (GitHub Pages ou serveur direct).
4. Carte **XIAO_ESP32S3**, *Tools → PSRAM → OPI PSRAM*, brancher le reTerminal en USB-C,
   téléverser.

L'écran se réveille, lit `status.json` (`refresh_s`), télécharge `dashboard.bin`, ne
redessine que si l'image a changé, puis se rendort. Bouton vert : rafraîchir tout de suite.

## Sur la télé

`https://h04k.github.io/tram-eink/` dans le navigateur de la télé (ou `http://<ip>:8080/`
en mode direct) : une page plein écran en noir et blanc, animée à la seconde, avec trois écrans :

- **le matin** (semaine, jusqu'à 30 min après le dernier tram) : compte à rebours avant de
  partir, trams en temps réel (lus directement chez TBM), séance du jour, pluie heure par heure ;
- **le soir** (semaine, le reste de la journée) : météo de ce soir et de demain, heure de départ
  de demain, actu en direct de toutes les rubriques (franceinfo, Sud Ouest Bordeaux, Air Journal),
  et les avions en style panneau d'embarquement : indicatif et route en lettres à palettes,
  tableau des vols (provenance, destination, appareil, altitude, vitesse, cap, distance) et
  minimap centrée sur la maison (N S E O, l'avion avance en direct, zoom selon sa distance) ;
- **le week-end** : la même chose, avec la météo du moment.

Avant le lever et après le coucher du soleil, l'écran se teinte progressivement d'orange
(lumière chaude, `WARM_MAX` dans `tv.html`).

### Avions à la seconde

Aucune source ADS-B gratuite n'autorise la lecture directe depuis un navigateur. Pour que la
télé les lise chaque seconde, il faut un relais :

- **Cloudflare Worker** (gratuit, rien à installer) : sur dash.cloudflare.com, *Workers →
  Create → Hello World*, remplacer le code par `worker/planes.js`, *Deploy*. Mettre son adresse
  (`https://xxx.workers.dev`) dans *Settings → Secrets and variables → Actions → Variables* du
  dépôt, sous le nom `ADSB_RELAY` (ou dans l'adresse de la page : `?adsb=https://xxx.workers.dev`).
- ou le **serveur maison** (`python -m tramdash.server`), qui sert `planes.json` rafraîchi chaque seconde.

Sans relais, les avions viennent du relevé de GitHub (toutes les 10 min) et l'écran l'indique.

Radio en bas à droite (France Inter, Nostalgie, Lofi, Nightwave Plaza, Yumi Co. Radio, Rainwave Chill et Gamesboro
pour les musiques de jeux vidéo) : **OK** sur la télécommande pour
lancer / couper, **◀ ▶** pour changer. Sur tablette : toucher ▶ pour lancer / couper, les
flèches pour changer, ou le nom de la station pour ouvrir la liste. Les positions d'avions sont en direct avec le serveur
maison ; sur GitHub Pages elles datent du dernier passage (10 min) et sont extrapolées.
`image.html` affiche simplement l'image de l'écran e-ink.

Pour tester une autre heure : `?now=2026-10-26T06:20` ; sans radio : `?radio=0`.

## Mise en ligne

1. Pousser ce dépôt sur GitHub.
2. *Settings → Pages → Source : GitHub Actions*.
3. *Actions → render → Run workflow* pour un premier rendu.
4. L'image est alors sur `https://<compte>.github.io/tram-eink/dashboard.png`.
