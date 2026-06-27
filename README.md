# metar-app

A Flask web app that accepts an ICAO airport code, fetches the latest METAR from the Aviation Weather Center API, and displays a plain-English weather report in the browser.

## Features

- Look up live weather for any ICAO airport (e.g. KJFK, EGLL, YSSY)
- Displays wind, visibility, cloud cover, temperature, pressure, and flight category
- Color-coded flight categories: VFR, MVFR, IFR, LIFR

## Getting Started

```bash
# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the dev server
python3 app.py
```

Then open http://localhost:5000 in your browser.

## Project Structure

```
app.py              Flask routes (GET / and POST /fetch)
metar_decoder.py    METAR → plain-English converter
templates/
  index.html        Single-page UI with vanilla JS
static/
  style.css         Styles (no external CSS dependencies)
```

## Data Source

Live METAR data is fetched from the [Aviation Weather Center API](https://aviationweather.gov/api/data/metar).

## Requirements

- Python 3.8+
- Flask
- requests
