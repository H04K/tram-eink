// Relais Cloudflare Worker : la télé ne peut pas lire adsb.lol directement (pas de CORS).
// Ce worker transmet /v2/point/<lat>/<lon>/<rayon en NM> et ajoute l'en-tête qui manque.
// Déploiement : Cloudflare -> Workers & Pages -> Create -> Import a repository (dossier worker),
// ou coller ce fichier dans un worker « Hello World ».
export default {
  async fetch(request) {
    const url = new URL(request.url);
    if (!/^\/v2\/point\/-?[\d.]+\/-?[\d.]+\/\d+$/.test(url.pathname)) {
      return new Response("usage : /v2/point/<lat>/<lon>/<nm>", { status: 400 });
    }
    const upstream = await fetch("https://api.adsb.lol" + url.pathname, {
      headers: { "User-Agent": "tram-eink (github.com/H04K/tram-eink)" },
      cf: { cacheTtl: 1, cacheEverything: true },  // une requête par seconde au plus vers adsb.lol
    });
    return new Response(upstream.body, {
      status: upstream.status,
      headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*",
                 "Cache-Control": "no-store" },
    });
  },
};
