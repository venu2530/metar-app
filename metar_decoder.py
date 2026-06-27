from datetime import datetime, timezone


def degrees_to_compass(degrees):
    directions = [
        "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
    ]
    return directions[round(float(degrees) / 22.5) % 16]


def hpa_to_inhg(hpa):
    return round(hpa * 0.02953, 2)


def celsius_to_fahrenheit(c):
    return round(c * 9 / 5 + 32, 1)


def decode_wx_string(wx_string):
    """Decode a METAR wxString like '-RA', 'TSRA', '+SNSQ' into plain English."""
    if not wx_string:
        return None

    intensity_map = {"-": "light", "+": "heavy"}

    # Order matters: longer descriptors first
    descriptors = [
        ("MI", "shallow"), ("BC", "patchy"), ("PR", "partial"),
        ("DR", "low drifting"), ("BL", "blowing"),
        ("TS", "thunderstorm"), ("FZ", "freezing"), ("SH", "showers"),
    ]

    phenomena = {
        "DZ": "drizzle", "RA": "rain", "SN": "snow",
        "SG": "snow grains", "IC": "ice crystals", "PL": "ice pellets",
        "GR": "hail", "GS": "small hail", "UP": "unknown precipitation",
        "FG": "fog", "BR": "mist", "HZ": "haze", "VA": "volcanic ash",
        "DU": "dust", "SA": "sand", "PY": "spray",
        "SQ": "squalls", "PO": "dust whirls", "DS": "dust storm",
        "SS": "sandstorm", "FC": "funnel cloud",
    }

    groups = []
    for group in wx_string.strip().split():
        pos = 0
        parts = []

        if group[pos:pos + 2] == "VC":
            parts.append("in the vicinity")
            pos += 2
        elif pos < len(group) and group[pos] in intensity_map:
            parts.append(intensity_map[group[pos]])
            pos += 1

        for code, label in descriptors:
            if group[pos:pos + 2] == code:
                if code == "TS" and pos + 2 < len(group):
                    parts.append("thunderstorm with")
                elif code == "SH":
                    pass  # appended after phenomenon below
                else:
                    parts.append(label)
                pos += 2
                break

        shower = False
        remaining = group[pos:]
        if "SH" in remaining:
            shower = True
            remaining = remaining.replace("SH", "")

        i = 0
        phenom_parts = []
        while i < len(remaining):
            code = remaining[i:i + 2]
            if code in phenomena:
                phenom_parts.append(phenomena[code])
                i += 2
            else:
                i += 1

        if phenom_parts:
            parts.append("/".join(phenom_parts))
        if shower:
            parts.append("showers")

        decoded = " ".join(parts).strip() or group
        groups.append(decoded)

    return ", ".join(groups).capitalize()


def decode_clouds(clouds):
    cover_names = {
        "SKC": "clear", "CLR": "clear", "NSC": "no significant cloud",
        "NCD": "no cloud detected", "CAVOK": "clear",
        "FEW": "few clouds", "SCT": "scattered clouds",
        "BKN": "broken clouds", "OVC": "overcast",
    }
    if not clouds:
        return "Clear skies"
    layers = []
    for layer in clouds:
        cover = cover_names.get(layer.get("cover", ""), layer.get("cover", ""))
        base = layer.get("base")
        layers.append(f"{cover} at {base:,} ft" if base is not None else cover)
    return ", ".join(layers)


def _get_ceiling(clouds):
    for layer in (clouds or []):
        if layer.get("cover") in ("BKN", "OVC"):
            return layer.get("base")
    return None


def _format_time(report_time):
    try:
        dt = datetime.fromisoformat(report_time.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y at %H:%M UTC")
    except Exception:
        return report_time


def decode_metar(data):
    result = {}

    result["raw"] = data.get("rawOb", "")
    result["station"] = data.get("icaoId", "")
    result["name"] = data.get("name", "")
    result["time"] = _format_time(data.get("reportTime", ""))

    # Wind
    wdir = data.get("wdir")
    wspd = data.get("wspd", 0) or 0
    wgst = data.get("wgst")

    if wspd == 0:
        result["wind"] = "Calm"
        result["wind_detail"] = "No significant wind"
    elif str(wdir) == "VRB":
        gust_str = f", gusting to {wgst} kt" if wgst else ""
        result["wind"] = f"Variable / {wspd} kt"
        result["wind_detail"] = f"Variable direction at {wspd} knots{gust_str}"
    elif wdir is not None:
        compass = degrees_to_compass(wdir)
        gust_str = f", gusting to {wgst} kt" if wgst else ""
        result["wind"] = f"{compass} / {wspd} kt" + (f" G{wgst}" if wgst else "")
        result["wind_detail"] = f"From the {compass} ({wdir}°) at {wspd} knots{gust_str}"
    else:
        result["wind"] = "Unknown"
        result["wind_detail"] = "Wind not reported"

    # Visibility
    visib_raw = data.get("visib")
    if visib_raw is not None:
        visib_str = str(visib_raw)
        try:
            v = float(visib_str.replace("+", ""))
            is_plus = visib_str.endswith("+") or v >= 10
            if is_plus:
                result["visibility"] = "10+ miles"
                result["visibility_detail"] = "10 or more statute miles — excellent visibility"
            else:
                qual = "good" if v >= 5 else "moderate" if v >= 3 else "poor" if v >= 1 else "very poor"
                result["visibility"] = f"{v} miles"
                result["visibility_detail"] = f"{v} statute miles — {qual}"
        except ValueError:
            result["visibility"] = visib_str
            result["visibility_detail"] = ""
    else:
        result["visibility"] = "N/A"
        result["visibility_detail"] = "Not reported"

    # Clouds
    clouds = data.get("clouds") or []
    result["sky"] = decode_clouds(clouds)

    cover_full = {
        "SKC": "Clear", "CLR": "Clear", "NSC": "No significant cloud",
        "FEW": "Few (1–2 oktas)", "SCT": "Scattered (3–4 oktas)",
        "BKN": "Broken (5–7 oktas)", "OVC": "Overcast (8 oktas)",
    }
    result["cloud_layers"] = [
        {
            "cover": cover_full.get(l.get("cover", ""), l.get("cover", "")),
            "base": f"{l['base']:,} ft" if l.get("base") is not None else "—",
        }
        for l in clouds
    ]

    ceiling = _get_ceiling(clouds)
    result["ceiling"] = f"{ceiling:,} ft" if ceiling is not None else "Unlimited"

    # Temperature / Dew point
    temp_c = data.get("temp")
    dewp_c = data.get("dewp")

    result["temperature"] = (
        f"{temp_c}°C / {celsius_to_fahrenheit(temp_c)}°F" if temp_c is not None else "N/A"
    )
    result["dewpoint"] = (
        f"{dewp_c}°C / {celsius_to_fahrenheit(dewp_c)}°F" if dewp_c is not None else "N/A"
    )

    if temp_c is not None and dewp_c is not None:
        spread = temp_c - dewp_c
        result["humidity_note"] = (
            "High humidity — fog or precipitation likely" if spread <= 2
            else "Moderate humidity" if spread <= 5
            else "Relatively dry air"
        )

    # Altimeter (API gives hPa, pilots use inHg)
    altim = data.get("altim")
    if altim is not None:
        result["altimeter"] = f"{hpa_to_inhg(altim)} inHg / {altim} hPa"
    else:
        result["altimeter"] = "N/A"

    # Weather phenomena
    wx = data.get("wxString") or data.get("presentWx")
    result["weather_raw"] = wx
    result["weather"] = decode_wx_string(wx)

    # Flight category
    cat = data.get("fltCat") or data.get("flightCategory")
    cat_map = {
        "VFR":  ("VFR",  "Visual Flight Rules — great flying conditions",         "#27ae60"),
        "MVFR": ("MVFR", "Marginal VFR — acceptable but reduced visibility",       "#2980b9"),
        "IFR":  ("IFR",  "Instrument Flight Rules — low ceiling or poor visibility", "#e67e22"),
        "LIFR": ("LIFR", "Low IFR — very poor conditions",                          "#c0392b"),
    }
    label, desc, color = cat_map.get(cat, (cat or "N/A", "Category unknown", "#7f8c8d"))
    result["flight_category"] = {"label": label, "desc": desc, "color": color}

    result["summary"] = _build_summary(result)
    return result


def _build_summary(r):
    parts = []

    if r.get("weather"):
        parts.append(r["weather"])

    sky = r.get("sky", "")
    if sky and "clear" not in sky.lower():
        parts.append(sky)
    elif "clear" in sky.lower():
        parts.append("clear skies")

    if r.get("temperature") and r["temperature"] != "N/A":
        parts.append(f"temperature {r['temperature']}")

    wind = r.get("wind_detail", "")
    if "calm" in wind.lower():
        parts.append("calm winds")
    elif wind and wind != "Wind not reported":
        parts.append(f"winds {wind[0].lower() + wind[1:]}")

    if r.get("visibility") and r["visibility"] != "N/A":
        parts.append(f"visibility {r['visibility']}")

    return ". ".join(p[0].upper() + p[1:] for p in parts) + ("." if parts else "")
