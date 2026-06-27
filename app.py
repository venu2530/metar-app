from flask import Flask, render_template, request, jsonify
import requests

from metar_decoder import decode_metar

app = Flask(__name__)

METAR_API_URL = "https://aviationweather.gov/api/data/metar"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/fetch", methods=["POST"])
def fetch_metar():
    body = request.get_json(silent=True) or {}
    airport = body.get("airport", "").strip().upper()

    if not airport:
        return jsonify({"error": "Please enter an airport code."}), 400

    if len(airport) < 3 or len(airport) > 4:
        return jsonify({"error": "Airport codes are 3–4 characters (e.g. KJFK, EGLL, YSSY)."}), 400

    try:
        resp = requests.get(
            METAR_API_URL,
            params={"ids": airport, "format": "json", "hours": 1},
            timeout=10,
        )
        # 204 = No Content — airport code not found in the database
        if resp.status_code == 204 or not resp.content:
            return jsonify({
                "error": f"No METAR data found for '{airport}'. "
                         "Check the ICAO code and try again."
            }), 404
        resp.raise_for_status()
        data = resp.json()
    except requests.Timeout:
        return jsonify({"error": "Request timed out. Please try again."}), 504
    except (requests.RequestException, ValueError):
        return jsonify({"error": "Failed to reach the weather service. Please try again."}), 503

    if not data:
        return jsonify({
            "error": f"No METAR data found for '{airport}'. "
                     "Check the ICAO code and try again."
        }), 404

    try:
        decoded = decode_metar(data[0])
    except Exception:
        return jsonify({"error": "Could not decode the METAR data."}), 500

    return jsonify(decoded)


if __name__ == "__main__":
    app.run(debug=True, port=5001)
