"""
fix_location.py  -  run ONCE from your project folder (where app.py is):   python fix_location.py

Problem: /predict always used the weather of "Bhopal" to calculate the disease-spread risk.
Fix:     the weather widget already knows the user's location (GPS or typed city).  That location
         is now sent with the scan, and the backend uses it.  Bhopal stays only as a last fallback
         (nothing sent).  Files touched: script.js, app.py   (backups: <file>.bak)
"""
import os, sys, shutil

def read(p):
    with open(p, "r", encoding="utf-8") as f: return f.read()

def patch(path, edits):
    text = read(path); orig = text
    for old, new, marker in edits:
        if marker in text: continue                       # already applied
        if text.count(old) != 1:
            print(f"[ERROR] {path}: expected text not found exactly once:\n        {old.strip().splitlines()[0][:80]!r}")
            return False
        text = text.replace(old, new)
    if text != orig:
        if not os.path.exists(path + ".bak"): shutil.copy(path, path + ".bak")
        with open(path, "w", encoding="utf-8", newline="") as f: f.write(text)
        print(f"[OK]    fixed {path}")
    else:
        print(f"[OK]    {path} already up to date")
    return True

js_edits = [
    # remember the last location the weather widget used (city search)
    ("      const data = await res.json();\n      this._usingCoords = false;\n",
     "      const data = await res.json();\n      this._usingCoords = false;\n      this.lastLocation = { city: data.city || city };\n",
     "this.lastLocation = { city: data.city || city };"),
    # ... and GPS location
    ("      const data = await res.json();\n      this._usingCoords = true;\n",
     "      const data = await res.json();\n      this._usingCoords = true;\n      this.lastLocation = { lat, lon, city: data.city };\n",
     "this.lastLocation = { lat, lon, city: data.city };"),
    # send it with the scan
    ("  if (currentFile) {\n    const fd = new FormData();\n    fd.append('file', currentFile);\n    requestBody = fd;\n  } else if (imageUrl) {\n    requestBody = JSON.stringify({ url: imageUrl });\n  } else {\n",
     "  // user's location (from the weather widget) -> the risk is calculated with THEIR weather\n"
     "  const loc = (typeof Weather !== 'undefined' && Weather.lastLocation) || {};\n"
     "  if (currentFile) {\n    const fd = new FormData();\n    fd.append('file', currentFile);\n"
     "    if (loc.lat != null && loc.lon != null) { fd.append('lat', loc.lat); fd.append('lon', loc.lon); }\n"
     "    if (loc.city) fd.append('city', loc.city);\n"
     "    requestBody = fd;\n  } else if (imageUrl) {\n"
     "    requestBody = JSON.stringify({ url: imageUrl, lat: loc.lat, lon: loc.lon, city: loc.city });\n  } else {\n",
     "user's location (from the weather widget)"),
]
py_edits = [
    ('            default_weather = get_weather("Bhopal")\n',
     '            # use the user\'s own location sent by the frontend; Bhopal only if nothing was sent\n'
     '            _body = request.get_json(silent=True) or {}\n'
     '            _lat  = request.form.get("lat") or _body.get("lat")\n'
     '            _lon  = request.form.get("lon") or _body.get("lon")\n'
     '            _city = request.form.get("city") or _body.get("city")\n'
     '            try:\n'
     '                default_weather = get_weather_by_coords(float(_lat), float(_lon))\n'
     '            except (TypeError, ValueError):\n'
     '                default_weather = get_weather((_city or "").strip() or "Bhopal")\n',
     "use the user's own location sent by the frontend"),
]

if __name__ == "__main__":
    if not (os.path.exists("app.py") and os.path.exists("script.js")):
        print("Run this inside the folder that contains app.py and script.js"); sys.exit(1)
    ok = patch("script.js", js_edits) & patch("app.py", py_edits)
    print("\nDone. Restart `python app.py`, hard-refresh (Ctrl+Shift+R), do a NEW scan." if ok
          else "\nSome edits were skipped (see errors). Send me this output.")
