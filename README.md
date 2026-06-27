# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this app does

A Flask web app that accepts an ICAO airport code, fetches the latest METAR from the Aviation Weather Center API, and returns a plain-English weather report in the browser.

## Commands

```bash
# First-time setup (Homebrew-managed Python requires a venv)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run dev server (http://localhost:5000)
python3 app.py

# Quick smoke test without a browser
python3 -c "
import sys, json; sys.path.insert(0, '.')
import app as a; a.app.config['TESTING'] = True
c = a.app.test_client()
r = c.post('/fetch', data=json.dumps({'airport':'KJFK'}), content_type='application/json')
print(json.loads(r.data).get('summary'))
"
```

## Architecture

```
app.py              Flask routes (GET / and POST /fetch)
metar_decoder.py    Pure-Python METAR → plain-English converter
templates/
  index.html        Single-page UI with inline vanilla JS
static/
  style.css         All styles; no external CSS dependencies
```

**Data flow:** Browser → `POST /fetch` → `app.py` fetches `https://aviationweather.gov/api/data/metar?ids=<ICAO>&format=json` → `decode_metar()` converts JSON → Flask returns decoded dict → JS renders cards.

## API notes

- **Endpoint:** `https://aviationweather.gov/api/data/metar?ids=ICAO&format=json&hours=1`
- **204 response** means the airport code was not found (empty body, no JSON).
- `altim` field is in **hPa** — multiply by 0.02953 to get inHg.
- `wdir=0, wspd=0` means calm (not north wind).
- `wdir` can be the string `"VRB"` for variable winds.
- `visib` can be the string `"10+"` (capped) or a plain float.
- `fltCat` is the flight category: `VFR`, `MVFR`, `IFR`, `LIFR`.

## Key decoder details (`metar_decoder.py`)

- `decode_metar(data)` — main entry point; takes the first element of the API JSON array.
- `decode_wx_string(wx)` — parses intensity prefix (`-`/`+`/`VC`), 2-char descriptors, 2-char phenomena codes, and `SH` suffix.
- `hpa_to_inhg(hpa)` — pressure unit conversion.
- `_get_ceiling(clouds)` — lowest BKN or OVC layer; returns `None` for unlimited.
