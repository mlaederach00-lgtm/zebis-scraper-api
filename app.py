from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

app = Flask(__name__)

# IDs der Klassen und Fächer auf zebis.ch
KLASSEN_ID = {"7": "31013", "8": "31014", "9": "31015"}
FACH_ID = {
    "deutsch": "31151",
    "englisch": "31152",
    "berufliche-orientierung": "31148",
    "ethik": "31153",
    "rzgesellschaft": "31162",
}

@app.route("/suche", methods=["GET"])
def suche_materialien():
    """
    Führt eine Live-Suche auf zebis.ch aus.
    Parameter:
      thema   – beliebiger Suchbegriff (z. B. 'Klimawandel', 'Berufsfindung', 'Migration' …)
      klasse  – 7 | 8 | 9
      fach    – deutsch | englisch | berufliche-orientierung | ethik | rzgesellschaft
    """
    thema = request.args.get("thema")
    klasse = request.args.get("klasse")
    fach = request.args.get("fach")

    if not thema or not klasse or not fach:
        return jsonify({"error": "Parameter 'thema', 'klasse' und 'fach' sind erforderlich."}), 400
    if klasse not in KLASSEN_ID or fach not in FACH_ID:
        return jsonify({"error": "Ungültige Klasse oder Fach"}), 400

    # dynamische Suche für beliebige Themen
    url = (
        f"https://www.zebis.ch/suche?keys={quote(thema)}"
        f"&f[0]=filter_schulstufe%3A{KLASSEN_ID[klasse]}"
        f"&f[1]=filter_fachbereich%3A{FACH_ID[fach]}"
    )

    res = requests.get(url)
    if res.status_code != 200:
        return jsonify({"error": f"Fehler beim Abruf ({res.status_code})"}), 500

    soup = BeautifulSoup(res.content, "html.parser")
    ergebnisse = []
    for item in soup.select(".search-result"):
        titel_tag = item.select_one(".title a")
        desc_tag = item.select_one(".search-snippet-info")
        if not titel_tag:
            continue
        ergebnisse.append({
            "titel": titel_tag.text.strip(),
            "beschreibung": desc_tag.text.strip() if desc_tag else "",
            "link": "https://www.zebis.ch" + titel_tag["href"]
        })

    return jsonify(ergebnisse)

@app.route("/")
def index():
    return "✅ Zebis Scraper API läuft – Suche über /​suche?thema=…"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
