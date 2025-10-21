from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import os

app = Flask(__name__)
# CORS für alle Routen erlauben (Actions-Test im Browser)
CORS(app, resources={r"/*": {"origins": "*"}})

KLASSEN_ID = {"7": "31013", "8": "31014", "9": "31015"}
FACH_ID = {
    "deutsch": "31151",
    "englisch": "31152",
    "berufliche-orientierung": "31148",
    "ethik": "31153",
    "rzgesellschaft": "31162",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/119.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de-CH,de;q=0.9,en;q=0.8",
}

def build_search_url(thema: str, klasse: str, fach: str) -> str:
    base = "https://www.zebis.ch/suche"
    return (
        f"{base}?keys={quote(thema)}"
        f"&f[0]=filter_schulstufe%3A{KLASSEN_ID[klasse]}"
        f"&f[1]=filter_fachbereich%3A{FACH_ID[fach]}"
    )

def parse_results(html: str):
    soup = BeautifulSoup(html, "html.parser")
    results = []

    # Variante A: klassische Suchseite
    for item in soup.select(".search-result"):
        a = item.select_one(".title a") or item.select_one("a")
        if not a:
            continue
        title = a.get_text(strip=True)
        href = a.get("href", "")
        link = ("https://www.zebis.ch" + href) if href.startswith("/") else href
        desc = item.select_one(".search-snippet-info") or item.select_one(".search-snippet")
        description = desc.get_text(strip=True) if desc else ""
        results.append({"titel": title, "beschreibung": description, "link": link})

    # Variante B: View-Listen
    if not results:
        for row in soup.select(".views-row"):
            a = row.select_one("a")
            if not a:
                continue
            title = a.get_text(strip=True)
            href = a.get("href", "")
            link = ("https://www.zebis.ch" + href) if href.startswith("/") else href
            desc = (
                row.select_one(".field--name-field-intro-text")
                or row.select_one(".field--name-body")
                or row.select_one(".teaser__text")
            )
            description = desc.get_text(strip=True) if desc else ""
            results.append({"titel": title, "beschreibung": description, "link": link})

    return results

@app.after_request
def add_cors_headers(resp):
    # Zusätzliche Sicherheits-/CORS-Header für Browser-Aufrufe (Actions-Test)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    resp.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    return resp

@app.route("/", methods=["GET"])
def index():
    return "✅ Zebis Scraper API · Endpunkt: /suche?thema=...&klasse=7|8|9&fach=deutsch|englisch|berufliche-orientierung|ethik|rzgesellschaft", 200

# Preflight für /suche erlauben
@app.route("/suche", methods=["OPTIONS"])
def suche_options():
    return ("", 204)

@app.route("/suche", methods=["GET"])
def suche_materialien():
    thema = (request.args.get("thema") or "").strip()
    klasse = (request.args.get("klasse") or "").strip()
    fach = (request.args.get("fach") or "").strip()

    if not thema or not klasse or not fach:
        return jsonify({"error": "Parameter 'thema', 'klasse' und 'fach' sind erforderlich."}), 400
    if klasse not in KLASSEN_ID:
        return jsonify({"error": f"Ungültige Klasse '{klasse}'. Erlaubt: 7, 8, 9"}), 400
    if fach not in FACH_ID:
        return jsonify({"error": f"Ungültiges Fach '{fach}'. Erlaubt: deutsch, englisch, berufliche-orientierung, ethik, rzgesellschaft"}), 400

    url = build_search_url(thema, klasse, fach)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
    except requests.RequestException as e:
        return jsonify({"error": "Netzwerkfehler beim Abruf", "details": str(e), "url": url}), 502

    # Wenn zebis 403 liefert, geben wir es als 502 mit erklärung zurück (nicht 403 an GPT)
    if resp.status_code != 200:
        return jsonify({
            "error": "Fehler beim Abruf von zebis.ch",
            "status": resp.status_code,
            "url": url
        }), 502

    items = parse_results(resp.text)
    return jsonify({
        "query": {"thema": thema, "klasse": klasse, "fach": fach},
        "sourceUrl": url,
        "count": len(items),
        "items": items
    }), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)


    


