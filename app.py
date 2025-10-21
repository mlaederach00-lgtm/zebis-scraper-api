from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import os

app = Flask(__name__)
CORS(app)

# 🔑 Dein ScraperAPI-Key (aktiv!)
SCRAPER_API_KEY = "863fd9ded8f037e3a8c5ed1b2909ebfb"

# IDs für Klassen und Fächer
KLASSEN_ID = {"7": "31013", "8": "31014", "9": "31015"}
FACH_ID = {
    "deutsch": "31151",
    "englisch": "31152",
    "berufliche-orientierung": "31148",
    "ethik": "31153",
    "rzgesellschaft": "31162",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/123.0 Safari/537.36",
    "Accept-Language": "de-CH,de;q=0.9,en;q=0.8",
}

def build_search_url(thema, klasse, fach):
    base = "https://www.zebis.ch/suche"
    return (
        f"{base}?keys={quote(thema)}"
        f"&f[0]=filter_schulstufe%3A{KLASSEN_ID[klasse]}"
        f"&f[1]=filter_fachbereich%3A{FACH_ID[fach]}"
    )

def parse_results(html):
    soup = BeautifulSoup(html, "html.parser")
    results = []

    # Variante A: klassische Suchseite
    for item in soup.select(".search-result"):
        a = item.select_one(".title a") or item.select_one("a")
        if not a:
            continue
        title = a.get_text(strip=True)
        href = a.get("href", "")
        link = "https://www.zebis.ch" + href if href.startswith("/") else href
        desc = item.select_one(".search-snippet-info") or item.select_one(".search-snippet")
        description = desc.get_text(strip=True) if desc else ""
        results.append({"titel": title, "beschreibung": description, "link": link})

    # Variante B: alternative Ansicht
    if not results:
        for row in soup.select(".views-row"):
            a = row.select_one("a")
            if not a:
                continue
            title = a.get_text(strip=True)
            href = a.get("href", "")
            link = "https://www.zebis.ch" + href if href.startswith("/") else href
            desc = (
                row.select_one(".field--name-field-intro-text")
                or row.select_one(".field--name-body")
                or row.select_one(".teaser__text")
            )
            description = desc.get_text(strip=True) if desc else ""
            results.append({"titel": title, "beschreibung": description, "link": link})

    return results

@app.route("/", methods=["GET"])
def home():
    return "✅ Zebis Scraper API mit ScraperAPI läuft. Endpunkt: /suche", 200

@app.route("/suche", methods=["GET"])
def suche_materialien():
    thema = (request.args.get("thema") or "").strip()
    klasse = (request.args.get("klasse") or "").strip()
    fach = (request.args.get("fach") or "").strip()

    if not thema or not klasse or not fach:
        return jsonify({"error": "Parameter 'thema', 'klasse' und 'fach' sind erforderlich."}), 400
    if klasse not in KLASSEN_ID:
        return jsonify({"error": f"Ungültige Klasse '{klasse}'. Erlaubt: 7,8,9"}), 400
    if fach not in FACH_ID:
        return jsonify({"error": f"Ungültiges Fach '{fach}'"}), 400

    zebis_url = build_search_url(thema, klasse, fach)
    proxy_url = f"https://api.scraperapi.com/?api_key={SCRAPER_API_KEY}&url={zebis_url}"

    try:
        resp = requests.get(proxy_url, headers=HEADERS, timeout=25)
        resp.raise_for_status()
    except requests.RequestException as e:
        return jsonify({
            "error": "Fehler beim Abruf über ScraperAPI",
            "details": str(e),
            "url": zebis_url
        }), 502

    items = parse_results(resp.text)
    return jsonify({
        "query": {"thema": thema, "klasse": klasse, "fach": fach},
        "sourceUrl": zebis_url,
        "count": len(items),
        "items": items
    }), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)

   
     

        



